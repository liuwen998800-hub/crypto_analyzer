#!/bin/bash
# 增强版虚拟币分析系统备份脚本

echo "💾 备份增强版虚拟币分析系统"
echo "================================"

# 配置
BACKUP_DIR="../backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="enhanced_crypto_analyzer_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# 创建备份目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_PATH"

echo "📁 备份目录: $BACKUP_PATH"

# 备份关键文件
echo "📦 备份源代码..."
cp -r ../src "$BACKUP_PATH/"
cp -r ../config "$BACKUP_PATH/"
cp -r ../web_dashboard "$BACKUP_PATH/"
cp ../*.py "$BACKUP_PATH/" 2>/dev/null || true
cp ../*.md "$BACKUP_PATH/" 2>/dev/null || true
cp ../*.sh "$BACKUP_PATH/" 2>/dev/null || true
cp ../requirements.txt "$BACKUP_PATH/" 2>/dev/null || true

# 备份配置文件（排除敏感信息）
echo "🔐 备份配置文件（脱敏）..."
if [ -f "../config/api_keys.yaml" ]; then
    # 创建脱敏版本
    sed 's/\(api_key\|api_secret\|bearer_token\|client_secret\|password\):.*/\1: "***HIDDEN***"/g' \
        "../config/api_keys.yaml" > "$BACKUP_PATH/config/api_keys_backup.yaml"
fi

# 备份数据库（如果存在）
echo "🗄️  备份数据库..."
if [ -d "../data" ]; then
    cp -r ../data "$BACKUP_PATH/"
fi

# 备份分析结果
echo "📊 备份分析结果..."
if [ -d "../results" ]; then
    cp -r ../results "$BACKUP_PATH/"
fi

# 创建备份信息文件
echo "📝 创建备份信息..."
cat > "$BACKUP_PATH/backup_info.txt" << EOF
增强版虚拟币分析系统备份
========================
备份时间: $(date)
备份版本: 增强版 v1.0
备份内容:
  - 源代码 (src/)
  - 配置文件 (config/)
  - Web仪表板 (web_dashboard/)
  - 数据库 (data/)
  - 分析结果 (results/)
  - 脚本文件 (*.sh, *.py)

系统状态:
$(ps aux | grep "python.*app_enhanced.py" | grep -v grep || echo "未运行")

API状态:
$(curl -s http://localhost:5001/api/status 2>/dev/null || echo "API不可用")

恢复说明:
1. 解压备份文件到项目目录
2. 恢复配置文件: cp config/api_keys_backup.yaml config/api_keys.yaml
3. 编辑 config/api_keys.yaml 填入实际API密钥
4. 安装依赖: pip install -r requirements.txt
5. 启动服务: ./web_dashboard/start_enhanced.sh
EOF

# 压缩备份
echo "🗜️  压缩备份文件..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# 计算备份大小
BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

echo "✅ 备份完成: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"

# 显示备份列表
echo ""
echo "📋 最近备份:"
ls -lh ../backups/*.tar.gz | tail -5

# 清理旧备份（保留最近10个）
echo ""
echo "🧹 清理旧备份..."
BACKUP_COUNT=$(ls ../backups/*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    OLD_BACKUPS=$(ls -t ../backups/*.tar.gz | tail -n +11)
    for backup in $OLD_BACKUPS; do
        echo "删除: $(basename $backup)"
        rm "$backup"
    done
fi

echo ""
echo "🔧 恢复命令:"
echo "  tar -xzf backups/${BACKUP_NAME}.tar.gz -C .."
echo ""
echo "🎉 备份完成！"