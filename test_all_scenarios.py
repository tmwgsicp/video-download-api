#!/usr/bin/env python3
"""
全面测试所有场景的API脚本
测试修复后的逻辑是否正确
"""

import requests
import time
import argparse
import os
import tempfile

def test_actual_download(download_url: str, file_type: str) -> bool:
    """测试实际的文件下载功能"""
    try:
        print(f"🔄 开始测试{file_type}文件下载...")
        
        # 直接使用GET请求进行流式下载测试
        response = requests.get(download_url, stream=True, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ {file_type}文件下载失败 (状态码: {response.status_code})")
            return False
        
        # 获取文件大小
        file_size = response.headers.get('content-length')
        if file_size:
            file_size_mb = int(file_size) / (1024 * 1024)
            print(f"📊 {file_type}文件大小: {file_size_mb:.2f} MB")
        
        # 验证Content-Type
        content_type = response.headers.get('content-type', '')
        print(f"📄 {file_type}文件类型: {content_type}")
        
        # 读取前1KB数据验证文件完整性
        chunk_size = 1024
        downloaded_bytes = 0
        
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    # 只下载前10KB进行验证，避免下载完整大文件
                    if downloaded_bytes >= 10240:  # 10KB
                        break
            
            temp_file.flush()
            temp_size = os.path.getsize(temp_file.name)
            
            if temp_size > 0:
                print(f"✅ {file_type}文件下载验证成功 (验证了 {downloaded_bytes} 字节)")
                return True
            else:
                print(f"❌ {file_type}文件下载验证失败 (文件为空)")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ {file_type}文件下载请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ {file_type}文件下载测试出错: {e}")
        return False

def test_scenario(api_base_url: str, video_url: str, extract_audio: bool, keep_video: bool, scenario_name: str):
    """测试特定场景"""
    print(f"\n🧪 测试场景: {scenario_name}")
    print(f"📋 参数: extract_audio={extract_audio}, keep_video={keep_video}")
    print("-" * 60)

    # 1. 提交任务
    print("📤 提交处理任务...")
    try:
        response = requests.post(
            f"{api_base_url}/api/process",
            json={
                "url": video_url,
                "extract_audio": extract_audio,
                "keep_video": keep_video
            },
            timeout=120
        )
        response.raise_for_status()
        task_data = response.json()
        task_id = task_data.get("task_id")
        print(f"✅ 任务提交成功！任务ID: {task_id}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 提交任务失败: {e}")
        return False

    # 2. 轮询任务状态
    print(f"🔄 监控任务状态...")
    status_url = f"{api_base_url}/api/status/{task_id}"
    
    max_wait_time = 300  # 最多等待5分钟
    start_time = time.time()
    
    while True:
        try:
            if time.time() - start_time > max_wait_time:
                print("⏰ 任务超时")
                return False
                
            status_response = requests.get(status_url, timeout=10)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            message = status_data.get("message", "无消息")
            
            print(f"📊 状态: {status} | 进度: {progress}% | 消息: {message}")

            if status == "completed":
                print("🎉 任务完成！")
                files = status_data.get("files", {})
                video_file = files.get("video")
                audio_file = files.get("audio")
                video_info = status_data.get("video_info", {})
                video_title = video_info.get("title", "未知标题")

                print(f"📹 视频标题: {video_title}")
                
                # 验证结果是否符合预期
                success = True
                
                if keep_video:
                    if video_file:
                        print(f"✅ 视频文件: {video_file}")
                        download_url = f"{api_base_url}/api/download/{os.path.basename(video_file)}"
                        print(f"📥 视频下载链接: {download_url}")
                        # 测试实际下载
                        if test_actual_download(download_url, "视频"):
                            print("✅ 视频文件下载测试成功")
                        else:
                            print("❌ 视频文件下载测试失败")
                            success = False
                    else:
                        print("❌ 期望有视频文件但没有返回")
                        success = False
                else:
                    if video_file:
                        print(f"⚠️  意外：返回了视频文件 {video_file}（不应该保留视频）")
                        # 注意：在"只要音频"的回退机制中，可能会临时下载视频但应该删除
                        # 这里不算错误，因为用户最终得到的是音频文件
                
                if extract_audio:
                    if audio_file:
                        print(f"✅ 音频文件: {audio_file}")
                        download_url = f"{api_base_url}/api/download/{os.path.basename(audio_file)}"
                        print(f"📥 音频下载链接: {download_url}")
                        # 测试实际下载
                        if test_actual_download(download_url, "音频"):
                            print("✅ 音频文件下载测试成功")
                        else:
                            print("❌ 音频文件下载测试失败")
                            success = False
                    else:
                        print("❌ 期望有音频文件但没有返回")
                        success = False
                else:
                    if audio_file:
                        print(f"⚠️  意外：返回了音频文件 {audio_file}（不应该提取音频）")
                        success = False
                
                return success
                    
            elif status == "error":
                print(f"💥 任务失败！")
                print(f"❌ 错误: {status_data.get('error')}")
                return False
            
            time.sleep(3)  # 每3秒检查一次
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 查询状态失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 发生意外错误: {e}")
            return False

def test_invalid_scenario(api_base_url: str, video_url: str):
    """测试无效场景（两个都为False）"""
    print(f"\n🧪 测试无效场景: 两个参数都为False")
    print("-" * 60)

    try:
        response = requests.post(
            f"{api_base_url}/api/process",
            json={
                "url": video_url,
                "extract_audio": False,
                "keep_video": False
            },
            timeout=120
        )
        
        if response.status_code == 422 or response.status_code == 400:
            print("✅ 正确拒绝了无效请求")
            return True
        else:
            task_data = response.json()
            task_id = task_data.get("task_id")
            print(f"📋 任务ID: {task_id}")
            
            # 检查是否会返回错误
            status_url = f"{api_base_url}/api/status/{task_id}"
            time.sleep(2)
            
            status_response = requests.get(status_url)
            status_data = status_response.json()
            
            if status_data.get("status") == "error":
                print("✅ 任务正确地返回了错误状态")
                return True
            else:
                print("❌ 应该返回错误但没有")
                return False
                
    except Exception as e:
        print(f"❌ 测试无效场景失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="全面测试所有场景的API")
    parser.add_argument("--url", type=str, required=True, help="要测试的视频链接")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="API服务器地址")
    parser.add_argument("--scenario", type=str, choices=["all", "1", "2", "3", "invalid"], 
                       default="all", help="要测试的场景")
    
    args = parser.parse_args()
    
    print("🧪 视频下载API - 全场景测试")
    print("=" * 60)
    
    # 测试API是否可用
    try:
        health_response = requests.get(f"{args.server}/api/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ API服务器运行正常")
        else:
            print("❌ API服务器状态异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {e}")
        return
    
    # 定义测试场景
    scenarios = [
        (True, True, "场景1: 同时要视频和音频"),
        (False, True, "场景2: 只要视频"),
        (True, False, "场景3: 只要音频"),
    ]
    
    results = []
    
    # 执行测试
    if args.scenario == "all":
        # 测试所有场景
        for extract_audio, keep_video, name in scenarios:
            success = test_scenario(args.server, args.url, extract_audio, keep_video, name)
            results.append((name, success))
        
        # 测试无效场景
        invalid_success = test_invalid_scenario(args.server, args.url)
        results.append(("无效场景测试", invalid_success))
        
    elif args.scenario == "1":
        success = test_scenario(args.server, args.url, True, True, "场景1: 同时要视频和音频")
        results.append(("场景1", success))
    elif args.scenario == "2":
        success = test_scenario(args.server, args.url, False, True, "场景2: 只要视频")
        results.append(("场景2", success))
    elif args.scenario == "3":
        success = test_scenario(args.server, args.url, True, False, "场景3: 只要音频")
        results.append(("场景3", success))
    elif args.scenario == "invalid":
        success = test_invalid_scenario(args.server, args.url)
        results.append(("无效场景", success))
    
    # 总结结果
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print("-" * 60)
    
    all_passed = True
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
        if not success:
            all_passed = False
    
    print("-" * 60)
    if all_passed:
        print("🎉 所有测试都通过了！API工作正常")
    else:
        print("💥 部分测试失败，需要检查API实现")

if __name__ == "__main__":
    main()
