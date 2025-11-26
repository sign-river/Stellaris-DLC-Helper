# Git 快速上传指南

## 初始化仓库并推送到GitHub

在项目目录 `e:\Stellaris-DLC-Helper` 中执行以下命令：

```powershell
# 1. 初始化Git仓库
git init

# 2. 添加所有文件
git add .

# 3. 创建初始提交
git commit -m "🎉 Initial commit: Stellaris DLC Helper v1.0.0"

# 4. 关联远程仓库
git remote add origin https://github.com/sign-river/Stellaris-DLC-Helper.git

# 5. 推送到GitHub（首次推送）
git push -u origin main
```

## 常用Git命令

```powershell
# 查看状态
git status

# 查看提交历史
git log --oneline

# 添加新文件
git add 文件名

# 提交更改
git commit -m "提交说明"

# 推送到远程
git push

# 拉取更新
git pull
```

## 后续更新流程

```powershell
# 1. 修改代码后
git add .

# 2. 提交更改
git commit -m "描述你的更改"

# 3. 推送到GitHub
git push
```

## 创建Release版本

1. 在GitHub网页上点击 "Releases"
2. 点击 "Create a new release"
3. 填写版本号：v1.0.0
4. 填写标题和说明
5. 上传打包好的 `Stellaris.DLC.Helper.v1.0.0.zip`
6. 点击 "Publish release"

## 注意事项

- 首次推送需要GitHub登录验证
- 推荐使用GitHub Desktop或配置SSH密钥
- 大文件（>100MB）不要提交到Git
