# 贡献指南

感谢你对 NetViz 项目的兴趣！我们欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请在 [Issues](../../issues) 中提交报告，并包含以下信息：

- 问题的清晰描述
- 复现步骤
- 期望的行为
- 实际的行为
- 截图（如适用）
- 运行环境信息（操作系统、Python 版本、Node.js 版本等）

### 功能建议

欢迎提出新功能建议！请在 Issues 中创建一个功能请求，描述：

- 你想要的功能
- 为什么这个功能有用
- 可能的实现方式

### 提交代码

1. **Fork 仓库** - 点击右上角的 Fork 按钮

2. **克隆你的 Fork**
   ```bash
   git clone https://github.com/your-username/netviz.git
   cd netviz
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/bug-description
   ```

4. **安装依赖**
   ```bash
   # 前端
   npm install
   
   # 后端
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **进行更改** - 编写代码，确保遵循项目的代码风格

6. **运行测试**
   ```bash
   # 后端测试
   cd backend
   pytest tests/ -v
   
   # 前端类型检查
   npm run typecheck
   ```

7. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
   
   提交信息请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
   - `feat:` 新功能
   - `fix:` Bug 修复
   - `docs:` 文档更新
   - `style:` 代码格式调整
   - `refactor:` 代码重构
   - `test:` 测试相关
   - `chore:` 构建/工具相关

8. **推送并创建 Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   然后在 GitHub 上创建 Pull Request

## 开发指南

### 项目结构

```
netviz/
├── src/                 # React 前端 (TypeScript)
│   ├── components/      # React 组件
│   ├── pages/           # 页面组件
│   ├── services/        # API 服务
│   └── types/           # TypeScript 类型定义
├── backend/             # Python 后端 (FastAPI)
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   └── services/    # 业务逻辑
│   └── tests/           # 测试文件
└── src-tauri/           # Tauri 桌面应用
```

### 代码风格

**前端 (TypeScript)**
- 使用 TypeScript 严格模式
- 避免使用 `any` 类型
- 组件使用函数式组件和 Hooks
- 使用 ESLint 和 Prettier 格式化

**后端 (Python)**
- 遵循 PEP 8 规范
- 使用类型注解
- 使用 `ruff` 进行代码检查
- 异步函数优先

### 测试

- 后端使用 `pytest` 进行测试
- 新功能应包含相应的测试用例
- 确保所有测试通过后再提交 PR

## 行为准则

参与此项目即表示你同意遵守我们的[行为准则](CODE_OF_CONDUCT.md)。

## 许可证

通过贡献代码，你同意你的贡献将在 [MIT License](LICENSE) 下发布。

## 联系方式

如有问题，可以通过 Issues 与我们联系。

再次感谢你的贡献！🎉
