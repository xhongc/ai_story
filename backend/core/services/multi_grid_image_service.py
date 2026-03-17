"""
多宫格图片处理服务
职责: 切割多宫格原图并保存切片结果
"""

from io import BytesIO
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
import uuid

import requests
from django.conf import settings
from PIL import Image

from core.utils.file_storage import image_storage


class MultiGridImageService:
    """多宫格图片处理服务"""

    @staticmethod
    def build_storage_url(relative_path: str) -> str:
        return f'/api/v1/content/storage/image/{relative_path}'

    @staticmethod
    def load_image(image_url: str) -> Image.Image:
        if image_url.startswith('/api/v1/content/storage/image/'):
            relative_path = image_url.split('/api/v1/content/storage/image/', 1)[1]
            image_path = Path(settings.STORAGE_ROOT) / 'image' / relative_path
            return Image.open(image_path).convert('RGB')

        response = requests.get(image_url, timeout=120)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGB')

    @staticmethod
    def _compute_segments(total_length: int, count: int, padding: int, gap: int) -> List[tuple]:
        usable = total_length - padding * 2 - gap * (count - 1)
        if usable <= 0:
            raise ValueError('无效的切图配置，实际可切区域小于等于 0')

        base = usable // count
        remainder = usable % count
        segments = []
        cursor = padding
        for index in range(count):
            size = base + (1 if index < remainder else 0)
            start = cursor
            end = start + size
            segments.append((start, end))
            cursor = end + gap
        return segments

    @classmethod
    def split_image(
        cls,
        image_url: str,
        grid_rows: int,
        grid_cols: int,
        tile_gap: int = 0,
        outer_padding: int = 0,
    ) -> Dict:
        if grid_rows <= 0 or grid_cols <= 0:
            raise ValueError('grid_rows 和 grid_cols 必须大于 0')

        image = cls.load_image(image_url)
        width, height = image.size
        x_segments = cls._compute_segments(width, grid_cols, outer_padding, tile_gap)
        y_segments = cls._compute_segments(height, grid_rows, outer_padding, tile_gap)

        tiles = []
        tile_index = 0
        for row_index, (top, bottom) in enumerate(y_segments):
            for col_index, (left, right) in enumerate(x_segments):
                tile = image.crop((left, top, right, bottom))
                buffer = BytesIO()
                tile.save(buffer, format='PNG')
                content = buffer.getvalue()
                _, relative_path = image_storage.save_file(
                    filename=f'multi_grid_tile_{uuid.uuid4().hex}.png',
                    content=content,
                )
                tiles.append({
                    'tile_index': tile_index,
                    'row_index': row_index,
                    'col_index': col_index,
                    'crop_box': {
                        'left': left,
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                    },
                    'tile_image_url': cls.build_storage_url(relative_path),
                    'width': tile.width,
                    'height': tile.height,
                })
                tile_index += 1

        return {
            'source_image_url': image_url,
            'source_width': width,
            'source_height': height,
            'grid_rows': grid_rows,
            'grid_cols': grid_cols,
            'tile_gap': tile_gap,
            'outer_padding': outer_padding,
            'tiles': tiles,
        }
