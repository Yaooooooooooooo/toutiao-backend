QINIU_ACCESS_KEY = 'UlWurkUaDseaEV6riHhialybOqE79AuXwLn_cU8_'
QINIU_SECRET_KEY = '_lKs6cnUQKVOAOFBYr9o4WQGRYj9TnX5A8NQpuwY'
QINIU_BUCKET_NAME = 'toutiao'

# SQLALCHEMY_DATABASE_URI = 'mysql://toutiao:Toutiao123456@172.17.0.136/toutiao'  # 数据库

GEETEST_ID = 'f00de9ed073bd781c94509932a309159'
GEETEST_KEY = 'da108e040c540f52233bf47e0e07baa8'

SQLALCHEMY_BINDS = {
    'bj-m1': 'mysql://toutiao:Toutiao123456@172.17.0.136/toutiao',
    'bj-m2': 'mysql://toutiao:Toutiao123456@172.17.0.136/toutiao',
    'bj-s1': 'mysql://toutiao:Toutiao123456@172.17.0.133/toutiao',
    'bj-s2': 'mysql://toutiao:Toutiao123456@172.17.0.133/toutiao',
    'masters': ['bj-m1', 'bj-m2'],
    'slaves': ['bj-s1', 'bj-s2'],
    'default': 'bj-m1'
}
