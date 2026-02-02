"""
Redis流式发布器
职责: 将流式数据发布到Redis Pub/Sub频道
遵循单一职责原则(SRP)
"""

import json
import logging
import time
from typing import Any, Dict, Optional
import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class RedisStreamPublisher:
    """
    Redis流式发布器

    负责将AI生成的流式数据发布到Redis Pub/Sub频道
    前端可通过WebSocket订阅该频道接收实时数据

    频道命名规范: ai_story:project:{project_id}:stage:{stage_name}
    """

    def __init__(self, project_id: str, stage_name: str):
        """
        初始化发布器

        Args:
            project_id: 项目ID
            stage_name: 阶段名称 (rewrite/storyboard/image_generation等)
        """
        self.project_id = project_id
        self.stage_name = stage_name
        self.channel = f"ai_story:project:{project_id}:stage:{stage_name}"

        # 使用连接池
        self.redis_client = self._get_redis_client()

        logger.info(f"初始化Redis发布器: {self.channel}")

    def _get_redis_client(self) -> redis.Redis:
        """
        获取Redis客户端
        使用连接池提高性能
        """
        try:
            # 从Django settings获取Redis Pub/Sub专用配置
            redis_url = getattr(settings, 'REDIS_PUBSUB_URL', 'redis://localhost:6379/2')

            # 解析Redis URL
            return redis.from_url(
                redis_url,
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            raise

    def publish(self, message: Dict[str, Any]) -> bool:
        """
        发布消息到Redis频道

        Args:
            message: 消息字典

        Returns:
            bool: 是否发布成功
        """
        try:
            # 添加时间戳
            if 'timestamp' not in message:
                message['timestamp'] = time.time()

            # 序列化为JSON
            message_json = json.dumps(message, ensure_ascii=False)

            # 发布到频道
            subscribers = self.redis_client.publish(self.channel, message_json)

            # logger.debug(f"发布消息到 {self.channel}: {message.get('type')} (订阅者: {subscribers})")

            return True

        except redis.RedisError as e:
            logger.error(f"Redis发布失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"消息发布异常: {str(e)}")
            return False

    def publish_token(self, content: str, full_text: str = "") -> bool:
        """
        发布Token消息 (流式文本片段)

        Args:
            content: 文本片段
            full_text: 累积的完整文本

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'token',
            'content': content,
            'full_text': full_text,
            'stage': self.stage_name,
            'project_id': self.project_id
        }
        return self.publish(message)

    def publish_stage_update(
        self,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        发布阶段状态更新消息

        Args:
            status: 状态 (processing/completed/failed)
            progress: 进度百分比 (0-100)
            message: 状态描述

        Returns:
            bool: 是否发布成功
        """
        msg = {
            'type': 'stage_update',
            'stage': self.stage_name,
            'status': status,
            'project_id': self.project_id
        }

        if progress is not None:
            msg['progress'] = progress

        if message:
            msg['message'] = message

        return self.publish(msg)

    def publish_done(self, full_text: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        发布完成消息

        Args:
            full_text: 完整生成结果
            metadata: 元数据 (tokens_used, latency_ms等)

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'done',
            'stage': self.stage_name,
            'project_id': self.project_id,
            'full_text': full_text
        }

        if metadata:
            message['metadata'] = metadata

        return self.publish(message)

    def publish_stage_completed(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        发布阶段完成消息 (用于通知前端刷新画布)

        Args:
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'stage_completed',
            'stage': self.stage_name,
            'project_id': self.project_id
        }

        if metadata:
            message['metadata'] = metadata

        return self.publish(message)

    def publish_error(self, error: str, retry_count: int = 0) -> bool:
        """
        发布错误消息

        Args:
            error: 错误描述
            retry_count: 重试次数

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'error',
            'stage': self.stage_name,
            'project_id': self.project_id,
            'error': error,
            'retry_count': retry_count
        }
        return self.publish(message)

    def publish_pipeline_done(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        发布流程完成消息 (用于全阶段订阅的结束信号)

        Args:
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'pipeline_done',
            'stage': self.stage_name,
            'project_id': self.project_id
        }

        if metadata:
            message['metadata'] = metadata

        return self.publish(message)

    def publish_pipeline_error(self, error: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        发布流程错误消息 (用于全阶段订阅的错误结束信号)

        Args:
            error: 错误描述
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        message = {
            'type': 'pipeline_error',
            'stage': self.stage_name,
            'project_id': self.project_id,
            'error': error
        }

        if metadata:
            message['metadata'] = metadata

        return self.publish(message)

    def publish_progress(
        self,
        current: int,
        total: int,
        item_name: str = ""
    ) -> bool:
        """
        发布进度消息 (用于批量处理场景)

        Args:
            current: 当前处理数量
            total: 总数量
            item_name: 当前处理项名称

        Returns:
            bool: 是否发布成功
        """
        progress = int((current / total) * 100) if total > 0 else 0

        message = {
            'type': 'progress',
            'stage': self.stage_name,
            'project_id': self.project_id,
            'current': current,
            'total': total,
            'progress': progress
        }

        if item_name:
            message['item_name'] = item_name

        return self.publish(message)

    def close(self):
        """
        关闭Redis连接
        """
        try:
            if self.redis_client:
                self.redis_client.close()
                logger.info(f"关闭Redis连接: {self.channel}")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {str(e)}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
