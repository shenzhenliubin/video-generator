# Design System — Video Generator

## Product Context
- **What this is:** YouTube 内容重新制作流水线 —— 自动从字幕提取到视频生成的端到端工具
- **Who it's for:** 想做知识类内容副业但不会做视频的人
- **Space/industry:** AI 视频生成工具 / 内容创作 SaaS
- **Project type:** Web 仪表盘应用

## Aesthetic Direction
- **Direction:** Modern SaaS Professional (现代 SaaS 专业风)
- **Decoration level:** Intentional (有意图的) — 细腻的背景纹理和边框处理，足够视觉层次
- **Mood:** 专业、高效、值得信赖。让用户感觉这是一个可靠的工具，能帮他们省去复杂的手工操作
- **Reference sites:** Linear, Vercel, HeyGen

## Typography
- **Display/Hero:** Satoshi (Fallback: Plus Jakarta Sans Bold) — 现代几何感，用于页面主标题和重要数据展示
- **Body:** Inter — 屏幕显示优化，出色的可读性，用于长文本和描述
- **UI/Labels:** Plus Jakarta Sans — 清晰的标签文字，用于按钮、菜单、导航
- **Data/Tables:** Geist Tabular (Fallback: JetBrains Mono) — 等宽数字，确保数据对齐
- **Code:** JetBrains Mono — 代码展示和技术内容
- **Loading:** Google Fonts CDN
- **Scale:**
  ```
  Display: 48/42/36/30/24
  H1: 32px, H2: 24px, H3: 20px, H4: 16px
  Body: 16px, Small: 14px, XSmall: 12px
  ```

## Color
- **Approach:** Balanced (平衡) — 主色 + 辅助色 + 语义颜色
- **Primary:** `#6366f1` (靛蓝) — 科技感、创新，避免 AI 工具常见的紫色渐变
- **Secondary:** `#10b981` (翠绿) — 成功状态、正向反馈
- **Neutrals:** 冷灰梯度
  - Light: `#f8fafc` → `#f1f5f9` → `#e2e8f0` → `#cbd5e1`
  - Dark: `#0f172a` → `#1e293b` → `#334155` → `#475569`
- **Semantic:**
  - Success: `#10b981` (绿)
  - Warning: `#f59e0b` (黄)
  - Error: `#ef4444` (红)
  - Info: `#3b82f6` (蓝)
- **Dark mode:** 主色调饱和度降低 10-15%，背景使用深冷灰

## Spacing
- **Base unit:** 4px
- **Density:** Comfortable (舒适) — 给用户呼吸空间
- **Scale:**
  ```
  2xs: 2px   (最紧凑)
  xs:  4px   (微小间距)
  sm:  8px   (小组件间距)
  md:  16px  (标准间距)
  lg:  24px  (大间距)
  xl:  32px  (章节间距)
  2xl: 48px  (区块间距)
  3xl: 64px  (页面级间距)
  ```

## Layout
- **Approach:** Grid-disciplined (网格规范) — 严格的列对齐和预测性布局
- **Grid:**
  - Sidebar: 240px fixed
  - Content: max 1400px, responsive
  - Breakpoints: 640px | 768px | 1024px | 1280px | 1400px
- **Max content width:** 1400px
- **Border radius:**
  ```
  sm: 6px   (按钮、输入框)
  md: 8px   (卡片)
  lg: 12px  (大卡片、模态框)
  xl: 16px  (特殊容器)
  full: 9999px (pill 按钮)
  ```

## Motion
- **Approach:** Minimal-functional (最小功能型) — 只保留有意义的过渡动画
- **Easing:**
  - Enter: ease-out
  - Exit: ease-in
  - Move: ease-in-out
- **Duration:**
  - Micro (悬停、焦点): 50-100ms
  - Short (工具提示、下拉): 150-250ms
  - Medium (模态框、页面切换): 250-400ms
  - Long (复杂动画): 400-700ms

## Component Library
- **UI Framework:** shadcn/ui + Tailwind CSS
- **Icons:** Lucide React
- **Forms:** React Hook Form + Zod
- **Data Tables:** TanStack Table
- **State Management:** Zustand (client) + React Query (server)

## Page Structure
- **Navigation:** 侧边栏固定 + 顶部栏
- **Main Pages:**
  1. Dashboard (仪表盘) — 概览、统计、最近任务
  2. Templates (风格管理) — 列表、创建、编辑
  3. Channels (频道监控) — 列表、添加、配置
  4. Videos (视频任务) — 列表、详情、进度
  5. Settings (设置) — 系统配置

## Dark Mode
- **Strategy:** 使用 CSS custom properties 实现
- **Implementation:**
  - 使用 `.dark-mode` 类切换
  - 主色调降低饱和度 10-15%
  - 背景色使用深冷灰梯度
  - 文字颜色反转并调整对比度

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-03-23 | Initial design system created | Created by /design-consultation based on AI video generation SaaS research |
| 2025-03-23 | Chose Indigo (#6366f1) over Purple gradient | Avoids "AI slop" aesthetic, more professional and unique |
| 2025-03-23 | Comfortable spacing density | Video creators spend long hours in the tool; breathing space reduces fatigue |
| 2025-03-23 | shadcn/ui over Ant Design | Better customization, lighter bundle, modern aesthetics |

## Implementation Notes
- Use Tailwind CSS v4+ with the custom color palette
- All components must support light/dark mode
- Maintain 4px base unit for all spacing
- Test responsive behavior at all breakpoints
- Ensure WCAG AA color contrast ratios
