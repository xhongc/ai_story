# AI Story Frontend

AI Story生成系统的Vue.js前端应用。

## 技术栈

- **Vue 2.7.14** - 渐进式JavaScript框架
- **Vue Router 3** - 官方路由管理器
- **Vuex 3** - 状态管理
- **Element UI** - UI组件库
- **Tailwind CSS** - 实用优先的CSS框架
- **Axios** - HTTP客户端
- **Webpack 5** - 模块打包工具

## 项目结构

```
frontend/
├── config/                 # Webpack配置
│   ├── webpack.common.js   # 通用配置
│   ├── webpack.dev.js      # 开发环境配置
│   └── webpack.prod.js     # 生产环境配置
├── public/                 # 静态资源
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── assets/            # 资源文件
│   │   ├── css/           # 样式文件
│   │   └── images/        # 图片资源
│   ├── components/        # 组件
│   │   ├── common/        # 通用组件
│   │   ├── layout/        # 布局组件
│   │   ├── projects/      # 项目相关组件
│   │   ├── content/       # 内容相关组件
│   │   ├── models/        # 模型相关组件
│   │   └── prompts/       # 提示词相关组件
│   ├── views/             # 页面组件
│   │   ├── projects/      # 项目页面
│   │   ├── prompts/       # 提示词页面
│   │   ├── models/        # 模型页面
│   │   ├── Layout.vue     # 主布局
│   │   └── NotFound.vue   # 404页面
│   ├── router/            # 路由配置
│   │   └── index.js
│   ├── store/             # Vuex状态管理
│   │   ├── modules/       # 模块
│   │   │   ├── projects.js
│   │   │   ├── prompts.js
│   │   │   ├── models.js
│   │   │   └── content.js
│   │   └── index.js
│   ├── services/          # API服务
│   │   ├── apiClient.js   # Axios配置
│   │   ├── projectService.js
│   │   ├── promptService.js
│   │   ├── modelService.js
│   │   └── contentService.js
│   ├── utils/             # 工具函数
│   │   ├── helpers.js     # 辅助函数
│   │   └── constants.js   # 常量定义
│   ├── App.vue            # 根组件
│   └── main.js            # 应用入口
├── .babelrc.js            # Babel配置
├── .eslintrc.js           # ESLint配置
├── postcss.config.js      # PostCSS配置
├── tailwind.config.js     # Tailwind配置
└── package.json

```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
```

应用将在 http://localhost:3000 启动。

### 3. 生产构建

```bash
npm run build
```

构建产物将生成在 `dist/` 目录。

### 4. 代码检查

```bash
npm run lint        # 检查代码
npm run lint:fix    # 自动修复
```

## Docker部署

### 开发环境

```bash
# 从项目根目录执行
docker-compose up frontend
```

### 生产环境

```bash
# 构建生产镜像
docker build -f docker/frontend.Dockerfile -t ai-story-frontend .

# 运行容器
docker run -p 3000:80 ai-story-frontend
```

## 核心功能

### 1. 项目管理
- 项目列表、创建、编辑、删除
- 项目详情查看
- 工作流阶段可视化
- 实时状态更新

### 2. 内容展示
- 分镜列表展示
- 生成图片预览
- 生成视频播放

### 3. 提示词管理
- 提示词集管理
- 模板查看和编辑

### 4. 模型管理
- 模型提供商列表
- 使用统计查看

## API集成

前端通过以下服务与后端通信:

- **RESTful API**: `/api/v1/*`

环境变量配置:

```env
VUE_APP_API_BASE_URL=http://localhost:8000/api/v1
```

## 代码规范

### 组件命名
- 使用 PascalCase: `ProjectList.vue`
- 组件名必须多个单词(避免与HTML元素冲突)

### 文件组织
- 每个组件一个文件
- 相关组件放在同一目录
- 通用组件放在 `components/common/`

### 样式约定
- 优先使用 Tailwind CSS 工具类
- 组件特定样式使用 scoped CSS
- 全局样式定义在 `assets/css/main.css`

### 状态管理
- 按功能模块划分 Vuex modules
- 异步操作放在 actions
- 避免直接修改 state,使用 mutations

## 开发建议

### 性能优化
- 使用路由懒加载
- 图片资源按需加载
- 合理使用 computed 和 watch
- 避免不必要的组件重渲染

### 错误处理
- API调用统一错误处理(apiClient拦截器)
- 组件级别错误边界
- 用户友好的错误提示

### 调试技巧
- 使用 Vue DevTools 浏览器扩展
- Chrome DevTools 网络面板监控API

## 待开发功能

- [ ] 用户认证和权限管理
- [ ] 图片查看器组件
- [ ] 视频播放器组件
- [ ] 批量操作功能
- [ ] 导出功能
- [ ] 主题切换
- [ ] 国际化支持

## 故障排查

### 常见问题

**1. 依赖安装失败**
```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
```

**2. 端口被占用**
```bash
# 修改 webpack.dev.js 中的端口配置
devServer: {
  port: 3001,  // 改成其他端口
}
```

**3. API请求失败**
- 检查后端服务是否启动
- 确认环境变量配置正确
- 查看浏览器控制台网络请求

## 贡献指南

1. 遵循项目代码规范
2. 编写必要的单元测试
3. 更新相关文档
4. 提交前运行 lint 检查

## License

MIT
