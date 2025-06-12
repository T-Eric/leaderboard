#!/bin/bash

# 创建临时目录
TEMP_DIR=$(mktemp -d /tmp/git_repos_XXXXXX)
echo "创建临时目录: $TEMP_DIR"

# 定义题号
PROBLEM_IDS=(1000 1001 1002 1003 1004)
OJ_TOKEN=acmoj-9b00d190090e0303fc684d1341e9918d

# 创建5个文件夹
for i in {1..5}; do
    REPO_DIR="$TEMP_DIR/repo$i"
    mkdir -p "$REPO_DIR"
    
    # 初始化Git仓库
    cd "$REPO_DIR"
    git init
    
    # 创建示例文件
    echo "这是仓库 $i 的README文件" > README.md
    echo "这是仓库 $i 的示例代码" > main.cpp
    
    # 添加并提交文件
    git add .
    git commit -m "Initial commit for repo $i"
    
    # 配置为Git Daemon可访问
    touch .git/git-daemon-export-ok
    
    echo "已创建并初始化仓库: $REPO_DIR"
done

# 启动Git Daemon服务
GIT_DAEMON_PID=""
start_git_daemon() {
    git daemon --reuseaddr --base-path="$TEMP_DIR" --export-all &
    GIT_DAEMON_PID=$!
    echo "Git Daemon已启动，PID: $GIT_DAEMON_PID"
    # 等待服务启动
    sleep 2
}

# 提交仓库到API
submit_repo() {
    local repo_num=$1
    local problem_id=${PROBLEM_IDS[$repo_num-1]}
    local repo_path="$TEMP_DIR/repo$repo_num"
    
    # 构建git协议URL (假设本机IP是10.181.70.149)
    # 注意：实际使用时请替换为您的服务器IP
    local git_url="git://10.181.70.149/repo$repo_num"
    
    echo "正在提交仓库 $repo_num 到题号 $problem_id..."
    
    # 进行API调用
    response=$(curl -s -X 'POST' \
        "https://acm.sjtu.edu.cn/OnlineJudge/api/v1/problem/$problem_id/submit" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -H 'Authorization: Bearer $OJ_TOKEN' \
        -d "public=false&language=git&code=$git_url")
    
    echo "API响应: $response"
    
    # 提取submission ID
    submission_id=$(echo $response | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "提交ID: $submission_id"
}

# 主执行流程
main() {
    # 启动Git Daemon
    start_git_daemon
    
    # 提交所有仓库
    for i in {1..5}; do
        submit_repo $i
        sleep 2  # 添加间隔防止API限流
    done
    
    echo "所有仓库已提交。Git Daemon将在30秒后关闭..."
    
    # 30秒后关闭Git Daemon
    sleep 30
    if [ ! -z "$GIT_DAEMON_PID" ]; then
        kill $GIT_DAEMON_PID
        echo "Git Daemon已关闭"
    fi
    
    echo "临时目录: $TEMP_DIR"
    echo "您可以手动删除临时目录，或保留以供检查"
}

# 执行主流程
main