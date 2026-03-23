"""
添加或更新监控频道到数据库
"""
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.storage.database import Database, Channel


def add_channel(
    channel_id: str,
    channel_name: str,
    channel_url: str = None,
    check_interval_seconds: int = 300,
    is_active: bool = True,
):
    """
    添加或更新监控频道

    Args:
        channel_id: YouTube频道ID (如 UCxxxxxxxxxxxxx)
        channel_name: 频道名称
        channel_url: 频道URL
        check_interval_seconds: 检查间隔（秒）
        is_active: 是否启用监控
    """
    settings = get_settings()
    db = Database(settings.database_url)
    db.create_tables()

    session = db.get_session()

    try:
        # 查找是否已存在
        existing = session.query(Channel).filter_by(channel_id=channel_id).first()

        if existing:
            # 更新
            existing.channel_name = channel_name
            existing.channel_url = channel_url or existing.channel_url
            existing.check_interval_seconds = check_interval_seconds
            existing.is_active = is_active
            print(f"✓ 更新频道: {channel_name}")
        else:
            # 新建
            if channel_url is None:
                channel_url = f"https://www.youtube.com/channel/{channel_id}"

            channel = Channel(
                channel_id=channel_id,
                channel_name=channel_name,
                channel_url=channel_url,
                check_interval_seconds=check_interval_seconds,
                is_active=is_active,
            )
            session.add(channel)
            print(f"✓ 添加频道: {channel_name}")

        session.commit()

        # 显示所有监控中的频道
        print("\n当前监控的频道:")
        active_channels = session.query(Channel).filter_by(is_active=True).all()
        for ch in active_channels:
            print(f"  - {ch.channel_name} ({ch.channel_id})")
            print(f"    检查间隔: {ch.check_interval_seconds}秒")
            print(f"    上次检查: {ch.last_checked_at}")

    finally:
        session.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python add_channel.py <频道ID> <频道名称> [检查间隔秒数]")
        print("示例: python add_channel.py UCxxxxxxxxxxxxx \"我的频道\" 600")
        sys.exit(1)

    channel_id = sys.argv[1]
    channel_name = sys.argv[2]
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 300

    add_channel(channel_id, channel_name, check_interval_seconds=interval)
