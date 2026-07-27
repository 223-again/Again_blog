---
title: 部署claude code，并且使用cc switch接入各类大模型
cat: tech
excerpt: windows系统下，具体步骤安装claude code，这是一个安装在你终端里的ai助手
date: 2026-07-10
---

## 部署 claude code

## 1

下载Node.js

前往>https://nodejs.org/zh-cn 下载node.js，直接下载即可

```
node --version
npm --version
```

检查node.js是否安装完成

## 2

安装git

前往>https://git-scm.com/ 不做版本要求

```
git --version
```

查看git是否安装好

## 3

安装claude code

Windows系统下通过powershell安装

```
##以管理员身份打开powershell
npm install -g @anthropic-ai claude-code
#验证安装
claude --version
```

这样就安装完了，一般情况需要修改配置，因为不能访问外网，但本人推荐使用cc switch  接入deepseek v4 pro（性价比之王）或者中转站使用外国模型。
