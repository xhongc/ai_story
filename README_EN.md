# AI Story - An AI-Powered Platform for Automated Story Video Creation

![logo](logo.png)

> 🎬 **From script to video in one click** — let AI help you create polished story videos with ease.

## Overview

AI Story is an AI-powered platform for automated story video production. Simply provide a story topic, and the system can complete the full workflow for you — including script writing, storyboard design, image generation, camera motion planning, and video production — making video creation faster, easier, and far more efficient.

---

## Text2Image Model
<div>
  <a href="https://share.302.ai/d6IJUM" target="_blank" rel="noopener noreferrer">
    <img src="/302_en.jpg" width="600" alt="302 AI" style="max-width: 100%;">
  </a>
</div>

[302.AI](https://share.302.ai/d6IJUM) is a pay-as-you-go enterprise AI resource hub that offers the latest and most comprehensive AI models and APIs on the market, along with a variety of ready-to-use online AI applications.

## 🚀 Quick Start

### Start Everything with Docker Compose

If you add a dedicated Celery service in your compose file, make sure it runs from `/app/backend`; otherwise Celery may fail with `Unable to load celery application. The module config was not found.`

```yml
  celery:
    image: xhongc/ai_story-backend
    working_dir: /app/backend
    command: celery -A config worker -l info -P gevent
```

```bash
# Start all services
docker-compose up -d

# Create an admin account
docker-compose exec backend python backend/manage.py createsuperuser
```

**Access URLs:**
- Frontend app: http://localhost:3000
- Backend admin: http://localhost:8010

---

## Interface Preview

![Video Generation](image-11.png)
![Video Generation](image-12.png)
![Video Generation](image-13.png)
![Video Generation](image-3.png)
![Video Generation](image-4.png)
![Video Generation](image-5.png)

**Director Mode** — currently in development, with more granular storyboard and video controls.
![Director Mode](image2.png)

**Sample Output Videos** — Search for `小小方圆669` on WeChat Channels.

---

## Core Features

### 1. Intelligent Script Rewriting
Enter a story topic or outline, and the AI automatically rewrites it into a complete script tailored for video presentation.

**Highlights:**
- Supports multiple writing styles, including narrative, educational, and emotional tones
- Custom prompt templates
- Multiple AI models available, such as OpenAI and Claude
- Version history with side-by-side comparison support

### 2. Automatic Storyboard Generation
Based on the rewritten script, the AI automatically breaks the story into scenes and generates a detailed storyboard.

**Highlights:**
- Intelligent scene segmentation
- Automatic generation of visual descriptions and voice-over text
- Professional image prompts for every shot
- Manual adjustment of storyboard order and content
- Configurable duration for each shot

### 3. AI Image Generation
Using storyboard prompts, the platform automatically calls AI image services to generate high-quality visuals.

**Highlights:**
- Supports multiple image generation platforms, including Stable Diffusion, DALL·E, and Midjourney
- Batch generation with real-time progress display
- Automatic retry on failure
- Image preview and management
- Prompt editing and regeneration support

### 4. Intelligent Camera Motion Planning
The AI analyzes each scene and automatically generates suitable camera movement plans.

**Highlights:**
- Multiple motion styles, including push, pull, pan, slide, zoom, and static shots
- Intelligent matching between scene content and camera motion type
- Customizable motion parameters such as speed and intensity
- Built-in motion preset library

### 5. Image-to-Video Generation
Combine static images with camera motion parameters to create dynamic video clips.

**Highlights:**
- Supports multiple video generation platforms, including Runway and Pika
- Custom resolution and frame rate
- Batch generation with real-time progress tracking
- Video preview and playback
- Automatic retry on failure

### 6. Project Management
Complete lifecycle management keeps your creative workflow organized from start to finish.

**Highlights:**
- Create, edit, and delete projects
- Real-time workflow status tracking
- Pause, resume, and retry support
- Stage rollback capabilities
- Project export, including video composition and subtitle generation
- Template saving and reuse

### 7. Prompt Management
A flexible prompt system helps AI better understand your creative intent.

**Highlights:**
- Create and manage prompt sets
- Template variables such as topic, style, and length
- Prompt version management
- Effectiveness evaluation and optimization suggestions
- Prompt testing and preview

### 8. Model Configuration
Manage all AI services in one place and switch flexibly between providers.

**Highlights:**
- Supports multiple AI service providers
- Multiple models can be configured for each stage
- Load balancing strategies, including round-robin, random, weighted, and least-load
- API connectivity testing
- Usage statistics and cost analysis
- Rate-limit configuration

---

## Workflow

```
Input Topic → Script Rewriting → Storyboard Generation → Image Generation → Camera Planning → Video Generation → Done
     ↓              ↓                   ↓                  ↓                 ↓                 ↓
Real-time progress display, with support for pausing, resuming, and retrying any stage
```

**Fully Automated** — start with one click and let the system complete every step.
**Real-Time Feedback** — monitor generation progress as it happens.
**Flexible Control** — fine-tune or regenerate every stage whenever needed.

---

## Technical Highlights

- **Modular architecture** — built on a pipeline chain-of-responsibility pattern for easy extension
- **Asynchronous processing** — powered by Celery task queues without blocking user actions
- **Real-time communication** — provides immediate progress feedback
- **Load balancing** — intelligently schedules multiple models for better stability
- **Fault tolerance** — automatic retry, failover, and error recovery
- **Containerized deployment** — one-click startup with Docker and isolated environments

---

## Use Cases

- 📱 **Short-form video creation** — quickly generate story videos for platforms like Douyin and Kuaishou
- 📚 **Educational content** — transform written content into visual videos
- 🎨 **Creative showcases** — present artistic ideas and concept designs as video
- 📖 **Children's stories** — turn fairy tales into animated story videos
- 🎬 **Video prototyping** — rapidly build script prototypes and storyboard previews

---

## Developer Documentation

For detailed technical documentation and development guidance, see:
- [Developer Guide](CLAUDE.md) — complete development documentation and command reference

---

## License

This project is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

- ✅ Allowed for personal learning and non-commercial use
- ✅ Modification and derivative works are allowed under the same license
- ❌ Commercial use is prohibited without commercial authorization

For commercial licensing, contact: `408737515@qq.com`

---

## Contact

<div>
<img src="/wc.jpg" width="250"> &nbsp;
</div>

- WeChat Channels: `小小方圆669`
- Author WeChat: `charlesnowed` (please mention **AI Story** when adding)
- Project URL: https://github.com/xhongc/ai_story
