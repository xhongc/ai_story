# AI Story - An AI-Powered Story Video Automation Platform

[中文版](README.md)

![logo](docs/images/logo.png)

<div class="column" align="middle">
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11-blue.svg" alt=""></a>
   <img src="https://img.shields.io/github/stars/xhongc/ai_story?color=informational&label=Stars">
  <img src="https://img.shields.io/docker/pulls/xhongc/ai_story-backend" alt="docker-pull-count" />
  <img src="https://img.shields.io/badge/platform-amd64/arm64-pink?style=plastic" alt="docker-platform" />
</div>

> 🎬 **From script to video in one click** - Let AI help you create professional story videos

## Overview

AI Story is an AI-powered platform for automatically creating story videos. Simply enter a story idea, and the system handles the entire workflow: script creation, storyboard design, image generation, camera-motion planning, and video production. It makes video creation simple and efficient.

---

## 💎 Sponsors

<table>
  <tr>
    <td width="190" align="center">
      <a href="https://metaso.cn/minimax-h3/?s=ai_story" target="_blank" rel="noopener"><img src="docs/images/sota.jpg" width="163" alt="秘塔科技 MetaSota"></a>
    </td>
    <td>
      <strong>MiniMax H3 Video Generation API | MetaSota</strong> MetaSota provides cost-effective MiniMax H3 video generation: <strong>768P at just CNY 0.09/second and 2K at CNY 0.15/second</strong>. It supports native 2K output, synchronized audio and video, and APIs compatible with the <strong>OpenAI protocol</strong>, as well as <strong>ComfyUI</strong> integration, with no GPU deployment required. 🎁 Register through the <a href="https://metaso.cn/minimax-h3/?s=ai_story" target="_blank" rel="noopener noreferrer">AI_STORY exclusive link</a> to receive bonus credits and special discounts.
    </td>
  </tr>
  <tr>
    <td width="190" align="center">
      <a href="https://www.compshare.cn/video-studio?ytag=GPU_YY_YX_git_ai_story" target="_blank" rel="noopener"><img src="docs/images/UCloud.png" width="163" alt="UCloud Computing"></a>
    </td>
    <td>
      <strong>UCloud Computing H3 Video Generation</strong> UCloud Computing offers cost-effective H3 video generation, including text-to-video, first-and-last-frame generation, and all-purpose reference. It supports videos up to 30 seconds long and 4K resolution, with <strong>768P at just CNY 0.08/second</strong>. API access, high concurrency for businesses, and self-service invoicing are available. Register through the <a href="https://www.compshare.cn/video-studio?ytag=GPU_YY_YX_git_ai_story" target="_blank" rel="noopener noreferrer">exclusive link</a> to receive free bonus credits.
    </td>
  </tr>
  <tr>
    <td width="190" align="center">
      <a href="https://5gtoken.com/login?dist=0494ce61a85d0e25" target="_blank" rel="noopener"><img src="docs/images/5g.png" width="163" alt="AI Super Factory"></a>
    </td>
    <td>
      <strong>AI Super Factory: Multiple Models, Unlimited Possibilities</strong> A one-stop AI model API aggregation platform compatible with the OpenAI API standard, supporting more than 100 leading models, including <strong>GPT-5, Claude 4.7, DeepSeek, and Gemini</strong>.
    </td>
  </tr>
</table>

---

## 🚀 Quick Start

### Start with Docker Compose

Create a `compose.yml` file locally:

```yml
services:

  # Redis cache and message queue
  redis:
    image: redis:7-alpine
    restart: unless-stopped

  # Django backend
  backend:
    image: xhongc/ai_story-backend
    restart: unless-stopped
    volumes:
      - ./data/backend:/app/backend/data
      - ./storage:/app/storage
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - REDIS_HOST=redis
    depends_on:
      - redis

  # Celery worker
  celery:
    image: xhongc/ai_story-backend
    working_dir: /app/backend
    command: celery -A config worker -l info -P gevent
    restart: unless-stopped
    volumes:
      - ./data/backend:/app/backend/data
      - ./storage:/app/storage
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - REDIS_HOST=redis
    depends_on:
      - redis

  # Vue frontend
  frontend:
    image: xhongc/ai_story-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

> **Note:** The Celery service must start in `/app/backend`; otherwise it will fail with `Unable to load celery application. The module config was not found.`

```bash
# Start all services
docker-compose up -d

# Alternatively
docker compose up -d

# Create an administrator account
docker-compose exec backend python backend/manage.py createsuperuser
```

**Access:**
- Frontend application: http://localhost:3000

---

## Interface Preview

![Video generation](docs/images/image-11.png)
![Video generation](docs/images/image-12.png)
![Video generation](docs/images/image-13.png)
![Video generation](docs/images/image-3.png)
![Video generation](docs/images/image-4.png)
![Video generation](docs/images/image-5.png)

**Director Mode** - In development, with more precise storyboard and video controls
![Director mode interface](docs/images/image14.png)
![Director mode interface](docs/images/image15.png)
![Director mode interface](docs/images/image16.png)

**Finished video samples** - Search for `小小方圆669` on WeChat Channels.

---

## Core Features

### 1. Intelligent Script Rewriting

Enter a story idea or outline, and AI automatically turns it into a complete script suitable for video.

**Highlights:**
- Multiple writing styles, including narrative, educational, and emotional
- Custom prompt templates
- Multiple AI models to choose from, including OpenAI and Claude
- Version history with comparison support

### 2. Automatic Storyboard Generation

Based on the rewritten script, AI automatically breaks the story into scenes and creates a detailed storyboard.

**Highlights:**
- Intelligent scene segmentation
- Automatic generation of visual descriptions and narration
- Professional image prompts for every shot
- Manual adjustment of shot order and content
- Configurable duration for each shot

### 3. AI Image Generation

Automatically call AI image-generation services to create high-quality images from storyboard prompts.

**Highlights:**
- Multiple image-generation platforms, including Stable Diffusion, DALL-E, and Midjourney
- Batch generation with real-time progress updates
- Automatic retries on failure
- Image preview and management
- Edit prompts and regenerate images

### 4. Intelligent Camera-Motion Planning

AI analyzes each scene and automatically creates an appropriate camera-motion plan.

**Highlights:**
- Multiple camera effects, including pans, tilts, push-ins, pull-outs, zooms, and static shots
- Intelligent matching of camera movements to scene content
- Customizable motion parameters, such as speed and intensity
- Preset library for camera movements

### 5. Image-to-Video Generation

Combine still images with camera-motion parameters to produce dynamic video clips.

**Highlights:**
- Multiple video-generation platforms, including Runway and Pika
- Customizable resolution and frame rate
- Batch generation with real-time progress tracking
- Video preview and playback
- Automatic retries on failure

### 6. Project Management

Manage the complete project lifecycle and keep every stage of the creative process organized.

**Highlights:**
- Create, edit, and delete projects
- Real-time workflow status tracking
- Pause, resume, and retry support
- Roll back to previous stages
- Export projects, including video composition and subtitle generation
- Save and reuse project templates

### 7. Prompt Management

A flexible prompt system that helps AI better understand your creative intent.

**Highlights:**
- Create and manage prompt collections
- Template variables, such as topic, style, and length
- Prompt version management
- Quality evaluation and optimization suggestions
- Prompt testing and preview

### 8. Model Configuration

Manage all AI services in one place and switch between them with ease.

**Highlights:**
- Support for multiple AI providers
- Multiple models configurable for each stage
- Load balancing through round-robin, random, weighted, and least-loaded strategies
- API connection testing
- Usage statistics and cost analysis
- Rate-limit configuration

---

## Workflow

```
Enter topic → Rewrite script → Generate storyboard → Generate images → Plan camera motion → Generate video → Done
      ↓              ↓                  ↓                  ↓                   ↓                    ↓
Real-time progress updates, with the ability to pause, resume, or retry any stage
```

**Fully automated** - Start with one click and let the system complete every step

**Real-time feedback** - Monitor generation progress as it happens

**Flexible control** - Manually adjust and regenerate any stage

---

## Technical Highlights

- **Modular architecture** - Built around a Pipeline and Chain of Responsibility design, making it easy to extend
- **Asynchronous processing** - Celery task queues keep user interactions responsive
- **Real-time communication** - Receive progress updates in real time
- **Load balancing** - Intelligent multi-model scheduling improves stability
- **Fault tolerance** - Automatic retries, failover, and error recovery
- **Containerized deployment** - One-click Docker startup with isolated environments

---

## Use Cases

- 📱 **Short-form video creation** - Quickly create story videos for TikTok, Kwai, and similar platforms
- 📚 **Educational content** - Turn written material into visual videos
- 🎨 **Creative showcases** - Present artwork and concept designs as videos
- 📖 **Children's stories** - Transform fairy tales into animated videos
- 🎬 **Video prototyping** - Quickly produce script prototypes and storyboard previews

---

## Inspiration

- My child refused to sleep after hearing the last story I made, so I quietly turned to this all-purpose bedtime-story library.

- I turned my child's doodles into a 10-page picture book. You only realize how useful this feature is after becoming a parent.

- I turned my cat into the lead of a palace-intrigue drama. I could not stop laughing.

- A beautifully shot micro-drama in five minutes. Who knew directing could be this accessible?

- For our anniversary, I gave my partner a novel about us. The result was spectacular.

- I fed one of my absurd dreams to AI, and it generated *Inception 2.0* for me.

## License

This project is licensed under the [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.

- ✅ Personal learning and non-commercial use are allowed
- ✅ Modification and derivative works are allowed, provided they use the same license
- ❌ Commercial use is prohibited without a separate commercial license

For commercial licensing, contact: 408737515@qq.com

---

## Contact

<div>
<img  src="docs/images/img0402.jpg" width="250">  &nbsp;
</div>

- WeChat Channels: 小小方圆669

- Author's WeChat: `charlesnowed` (please include **AI Story** in your friend request)

- [TG announcement channel](https://t.me/+YwhET7N5a0E3M2E1)

- [TG discussion group](https://t.me/+HHlaG6o3hYFjYjI1)

- Project repository: https://github.com/xhongc/ai_story
