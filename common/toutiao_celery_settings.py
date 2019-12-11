class CeleryConfig(object):
    """
    Celery默认配置
    """
    broker_url = 'amqp://admin:rabbitmq@localhost:5672/delron'

    task_routes = {
        'sms.*': {'queue': 'sms'},
    }

    # 阿里短信服务
    DYSMS_ACCESS_KEY_ID = 'LTAIv7WeJTLzLDrq'
    DYSMS_ACCESS_KEY_SECRET = 'NPY1AL4GTuL8kJPB4b1DMoAfCuTf3K'
