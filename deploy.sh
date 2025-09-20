# 视频下载API部署脚本
# 专注Ubuntu/Debian系统部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
PROJECT_NAME="video-download-api"
SERVICE_NAME="video-download-api"
SERVICE_PORT=8000
DEPLOY_USER="apiuser"
PROJECT_DIR="/home/$DEPLOY_USER/$PROJECT_NAME"

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检测操作系统
detect_os() {
    log_info "检测操作系统..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_VERSION="$VERSION_ID"
        
        case "$ID" in
            ubuntu|debian)
                OS_TYPE="debian"
                PACKAGE_MANAGER="apt"
                ;;
            *)
                if [[ "$ID_LIKE" == *"debian"* ]]; then
                    OS_TYPE="debian"
                    PACKAGE_MANAGER="apt"
                else
                    log_error "不支持的操作系统: $ID"
                    echo "本脚本仅支持Ubuntu/Debian系统"
                    exit 1
                fi
                ;;
        esac
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    
    log_success "检测到操作系统: $ID $VERSION_ID (类型: $OS_TYPE)"
}

# 检测Python版本
check_python_version() {
    log_info "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "未找到python3，请先安装Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    log_info "当前Python版本: $PYTHON_VERSION"
    
    if ! python3 -m pip --version &> /dev/null; then
        log_warning "pip3不可用，稍后尝试安装"
    fi
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]; then
        log_error "Python版本过低，当前: $PYTHON_VERSION，要求: 3.8+"
        
        if [ -f "upgrade_python.sh" ]; then
            echo "请运行升级脚本: chmod +x upgrade_python.sh && sudo ./upgrade_python.sh"
            read -p "是否现在运行升级脚本？(y/N): " run_upgrade
            if [[ "$run_upgrade" =~ ^[Yy]$ ]]; then
                chmod +x upgrade_python.sh
                ./upgrade_python.sh || {
                    log_error "升级失败，部署终止"
                    exit 1
                }
                check_python_version
            else
                exit 1
            fi
        else
            echo "请下载并运行 Python 升级脚本"
            exit 1
        fi
    else
        log_success "Python版本兼容"
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    case "$OS_TYPE" in
        debian)
            apt update -qq
            apt install -y \
                python3-pip python3-venv python3-dev \
                git curl wget unzip \
                build-essential ffmpeg
            
            if ! python3 -m venv --help &>/dev/null; then
                apt install -y python3-venv
            fi
            ;;
    esac
    
    log_success "系统依赖安装完成"
}

# 验证FFmpeg
verify_ffmpeg() {
    log_info "验证FFmpeg安装..."
    
    if command -v ffmpeg &> /dev/null; then
        local ffmpeg_version=$(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)
        log_success "FFmpeg已安装: $ffmpeg_version"
    else
        log_error "FFmpeg未安装，音频提取功能将不可用"
        echo "请手动安装FFmpeg或重新运行脚本"
        exit 1
    fi
}

# 创建用户
create_user() {
    log_info "创建部署用户..."
    
    if ! id "$DEPLOY_USER" &>/dev/null; then
        if useradd -m -s /bin/bash "$DEPLOY_USER" 2>/dev/null; then
            log_success "创建用户: $DEPLOY_USER"
        else
            log_warning "用户创建失败，使用root用户运行"
            DEPLOY_USER="root"
            PROJECT_DIR="/opt/$PROJECT_NAME"
        fi
    else
        log_info "用户已存在: $DEPLOY_USER"
    fi
    
    mkdir -p "$PROJECT_DIR"
    if [ "$DEPLOY_USER" != "root" ]; then
        chown -R "$DEPLOY_USER:$DEPLOY_USER" "$PROJECT_DIR" 2>/dev/null || {
            log_warning "权限设置失败"
        }
    fi
}

# 复制项目文件
copy_project() {
    log_info "复制项目文件到 $PROJECT_DIR..."
    
    # 复制核心文件
    for file in start.py requirements.txt api; do
        if [ -e "$file" ]; then
            cp -r "$file" "$PROJECT_DIR/"
        else
            log_error "未找到文件: $file"
            exit 1
        fi
    done
    
    # 创建临时目录
    mkdir -p "$PROJECT_DIR/temp"
    
    # 设置权限
    if [ "$DEPLOY_USER" != "root" ]; then
        chown -R "$DEPLOY_USER:$DEPLOY_USER" "$PROJECT_DIR" 2>/dev/null || {
            log_warning "权限设置失败"
        }
    fi
    
    log_success "项目文件复制完成"
}

# 创建虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    
    cd "$PROJECT_DIR"
    
    if [ "$DEPLOY_USER" = "root" ]; then
        python3 -m venv venv
    else
        sudo -u "$DEPLOY_USER" python3 -m venv venv
    fi
    
    if [ ! -f "venv/bin/activate" ]; then
        log_error "虚拟环境创建失败"
        exit 1
    fi
    
    log_success "虚拟环境创建完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    cd "$PROJECT_DIR"
    
    # 使用默认依赖文件
    local req_file="requirements.txt"
    log_info "使用依赖文件: $req_file"
    
    # 安装依赖的函数
    install_deps() {
        local file="$1"
        if [ "$DEPLOY_USER" = "root" ]; then
            source venv/bin/activate
            pip install --upgrade pip -q
            pip install -r "$file" -q
        else
            sudo -u "$DEPLOY_USER" bash -c "
                cd '$PROJECT_DIR'
                source venv/bin/activate
                pip install --upgrade pip -q
                pip install -r '$file' -q
            " || {
                log_warning "su命令失败，尝试直接安装"
                source venv/bin/activate
                pip install --upgrade pip -q
                pip install -r "$file" -q
            }
        fi
    }
    
    # 尝试安装主依赖文件
    if install_deps "$req_file" 2>/dev/null; then
        log_success "Python依赖安装成功 (使用: $req_file)"
        return 0
    fi
    
    # 如果主依赖安装失败，尝试fallback版本
    log_warning "主依赖安装失败，创建紧急fallback版本..."
    
    # 创建最保守的fallback依赖文件
    cat > "requirements-fallback.txt" << 'EOF'
# 紧急fallback版本 - 最保守的依赖版本
fastapi>=0.85.0
uvicorn>=0.18.0
requests>=2.20.0
pydantic>=1.8.0
python-multipart>=0.0.3
aiofiles>=0.7.0
pyyaml>=5.1.0
aiohttp>=3.6.0
yt-dlp>=2023.12.0
EOF
    
    log_info "尝试使用fallback版本..."
    if install_deps "requirements-fallback.txt" 2>/dev/null; then
        log_success "Python依赖安装成功 (使用fallback版本)"
        return 0
    fi
    
    # 最后的尝试 - 逐个安装
    log_warning "fallback版本也失败，尝试逐个安装核心依赖..."
    
    local core_packages=("fastapi" "uvicorn" "requests" "pydantic" "aiofiles" "pyyaml" "aiohttp" "yt-dlp")
    
    if [ "$DEPLOY_USER" = "root" ]; then
        source venv/bin/activate
        pip install --upgrade pip -q
        for package in "${core_packages[@]}"; do
            pip install "$package" -q && log_info "✓ $package 安装成功" || log_warning "✗ $package 安装失败"
        done
    else
        sudo -u "$DEPLOY_USER" bash -c "
            cd '$PROJECT_DIR'
            source venv/bin/activate
            pip install --upgrade pip -q
            for package in fastapi uvicorn requests pydantic aiofiles pyyaml aiohttp yt-dlp; do
                pip install \"\$package\" -q && echo \"✓ \$package 安装成功\" || echo \"✗ \$package 安装失败\"
            done
        "
    fi
    
    log_success "核心依赖安装完成（逐个安装模式）"
}

# 创建系统服务
create_service() {
    log_info "创建系统服务..."
    
    if ! command -v systemctl &> /dev/null; then
        log_error "systemctl不可用，无法配置系统服务"
        echo "请手动启动服务，参考部署指南"
        return 1
    fi
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Video Download API Service
After=network.target

[Service]
Type=simple
User=$DEPLOY_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python start.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "系统服务创建完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    if ! command -v systemctl &> /dev/null; then
        log_info "跳过防火墙配置"
        return 0
    fi
    
    if systemctl is-active --quiet ufw; then
        ufw allow "$SERVICE_PORT/tcp" >/dev/null 2>&1
        log_success "ufw防火墙已配置"
    elif systemctl is-active --quiet firewalld; then
        firewall-cmd --permanent --add-port="$SERVICE_PORT/tcp" >/dev/null 2>&1
        firewall-cmd --reload >/dev/null 2>&1
        log_success "firewalld防火墙已配置"
    else
        log_info "未检测到活动防火墙"
    fi
}

# 测试服务配置
test_service_config() {
    log_info "测试服务配置..."
    
    cd "$PROJECT_DIR"
    
    # 测试Python模块导入
    if [ "$DEPLOY_USER" = "root" ]; then
        source venv/bin/activate
        python3 -c "import fastapi, uvicorn; print('✅ 核心依赖正常')" 2>/dev/null || {
            log_error "核心依赖测试失败"
            return 1
        }
    else
        sudo -u "$DEPLOY_USER" bash -c "
            cd '$PROJECT_DIR'
            source venv/bin/activate
            python3 -c 'import fastapi, uvicorn; print(\"✅ 核心依赖正常\")' 2>/dev/null
        " || {
            source venv/bin/activate
            python3 -c "import fastapi, uvicorn; print('✅ 核心依赖正常')" 2>/dev/null || {
                log_error "核心依赖测试失败"
                return 1
            }
        }
    fi
    
    # API模块导入测试
    log_info "测试API模块导入..."
    if [ "$DEPLOY_USER" = "root" ]; then
        source venv/bin/activate
        export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
        python3 -c "
try:
    from api.main import app
    print('✅ API模块导入成功')
except Exception as e:
    print(f'❌ API模块导入失败: {e}')
    import traceback
    traceback.print_exc()
    raise
" 2>/dev/null || {
            log_error "API模块导入失败，检查错误详情："
            python3 -c "
try:
    from api.main import app
except Exception as e:
    print(f'详细错误: {e}')
    import traceback
    traceback.print_exc()
"
            return 1
        }
    else
        sudo -u "$DEPLOY_USER" bash -c "
            cd '$PROJECT_DIR'
            source venv/bin/activate
            export PYTHONPATH='$PROJECT_DIR:\$PYTHONPATH'
            python3 -c '
try:
    from api.main import app
    print(\"✅ API模块导入成功\")
except Exception as e:
    print(f\"❌ API模块导入失败: {e}\")
    import traceback
    traceback.print_exc()
    raise
'
        " 2>/dev/null || {
            log_error "API模块导入失败，检查错误详情："
            sudo -u "$DEPLOY_USER" bash -c "
                cd '$PROJECT_DIR'
                source venv/bin/activate
                export PYTHONPATH='$PROJECT_DIR:\$PYTHONPATH'
                python3 -c '
try:
    from api.main import app
except Exception as e:
    print(f\"详细错误: {e}\")
    import traceback
    traceback.print_exc()
'
            " || {
                source venv/bin/activate
                export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
                python3 -c "
try:
    from api.main import app
except Exception as e:
    print(f'详细错误: {e}')
    import traceback
    traceback.print_exc()
"
                return 1
            }
        }
    fi
    
    log_success "服务配置测试通过"
    return 0
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    if ! test_service_config; then
        log_error "服务配置测试失败，终止部署"
        exit 1
    fi
    
    # 检查端口冲突
    if command -v netstat &> /dev/null && netstat -tulpn 2>/dev/null | grep -q ":$SERVICE_PORT "; then
        log_warning "端口$SERVICE_PORT已被占用，尝试停止冲突服务"
        local pid=$(netstat -tulpn 2>/dev/null | grep ":$SERVICE_PORT " | awk '{print $7}' | cut -d'/' -f1 | head -1)
        if [ -n "$pid" ] && [ "$pid" != "-" ]; then
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    elif command -v ss &> /dev/null && ss -tulpn 2>/dev/null | grep -q ":$SERVICE_PORT "; then
        log_warning "端口$SERVICE_PORT已被占用（ss检测）"
    fi
    
    # 启动服务
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl start "$SERVICE_NAME"
    
    # 检查服务状态
    sleep 3
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "服务启动成功"
        
        # API检查
        log_info "等待API启动..."
        local attempts=0
        while [ $attempts -lt 8 ]; do
            if curl -s "http://localhost:$SERVICE_PORT/api/health" > /dev/null 2>&1; then
                log_success "API服务正常运行"
                echo ""
                echo "🎉 部署完成！"
                echo "==============================================="
                echo "🌐 服务地址: http://localhost:$SERVICE_PORT"
                echo "🔍 API文档: http://localhost:$SERVICE_PORT/docs"
                echo "❤️ 健康检查: http://localhost:$SERVICE_PORT/api/health"
                echo ""
                echo "🛠️ 管理命令:"
                echo "  查看状态: systemctl status $SERVICE_NAME"
                echo "  查看日志: journalctl -u $SERVICE_NAME -f"
                echo "  停止服务: systemctl stop $SERVICE_NAME"
                echo "  重启服务: systemctl restart $SERVICE_NAME"
                echo ""
                echo "🚀 性能提示:"
                echo "  - 服务已启用自动重启，崩溃后会自动恢复"
                echo "  - 日志通过systemd管理，支持日志轮转"
                echo "  - 使用专用用户运行，提升安全性"
                return 0
            fi
            attempts=$((attempts + 1))
            sleep 2
        done
        
        log_warning "API服务响应超时，请检查日志"
        echo "查看日志: journalctl -u $SERVICE_NAME -f"
    else
        log_error "服务启动失败"
        echo ""
        echo "🔍 调试信息:"
        echo "1. 查看服务状态: systemctl status $SERVICE_NAME -l"
        echo "2. 查看错误日志: journalctl -u $SERVICE_NAME -n 20"
        echo "3. 手动测试: sudo -u $DEPLOY_USER bash -c 'cd $PROJECT_DIR && source venv/bin/activate && python start.py'"
        
        echo ""
        echo "🔍 最近错误:"
        journalctl -u "$SERVICE_NAME" -n 5 --no-pager || echo "无法获取日志"
        exit 1
    fi
}

# 主函数
main() {
    echo "🚀 视频下载API部署脚本"
    echo "专注Ubuntu/Debian系统部署"
    echo "============================"
    
    # 检查root权限
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        echo "请使用: sudo $0"
        exit 1
    fi
    
    # 执行部署步骤
    detect_os
    check_python_version
    install_system_deps
    verify_ffmpeg
    create_user
    copy_project
    create_venv
    install_python_deps
    create_service
    configure_firewall
    start_service
}

# 运行主函数
main "$@"