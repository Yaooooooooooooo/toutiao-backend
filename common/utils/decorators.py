from flask import g
from functools import wraps


def login_required(func):
    """
    用户必须认证通过装饰器
    使用方法：放在method_decorators中
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.user_id:
            return {'message': 'User must be authorized.'}, 401
        else:
            return func(*args, **kwargs)

    return wrapper
