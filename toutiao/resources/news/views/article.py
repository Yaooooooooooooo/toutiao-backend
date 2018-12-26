from flask_restful import Resource, abort
from flask import g, current_app
from sqlalchemy.orm import load_only
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
import re
import random

from models.news import Article, ArticleContent, Attitude
from toutiao.main import rpc_cli
from rpc import user_reco_pb2, user_reco_pb2_grpc
from .. import constants
from utils import parser
from cache import article as cache_article
from cache import user as cache_user
from models import db
from utils.decorators import login_required, validate_token_if_using
from utils.logging import write_trace_log


class ArticleResource(Resource):
    """
    文章
    """
    method_decorators = [validate_token_if_using]

    def _feed_similar_articles(self, article_id):
        """
        获取相似文章
        :param article_id:
        :return:
        """
        req = user_reco_pb2.Article()
        req.article_id = article_id
        req.article_num = constants.RECOMMENDED_SIMILAR_ARTICLE_MAX

        stub = user_reco_pb2_grpc.UserRecommendStub(rpc_cli)
        resp = stub.article_recommend(req)

        return resp.article_id

    def get(self, article_id):
        """
        获取文章详情
        :param article_id: int 文章id
        """
        # 写入埋点日志
        qs_parser = RequestParser()
        qs_parser.add_argument('trace', type=inputs.regex(r'^.+$'), required=False, location='args')
        args = qs_parser.parse_args()
        if args.trace:
            write_trace_log(args.trace)

        user_id = g.user_id

        # 查询文章数据
        exist = cache_article.determine_article_exists(article_id)
        if not exist:
            abort(404, message='The article does not exist.')

        article = cache_article.get_article_detail(article_id)

        article['is_followed'] = False
        article['attitude'] = None

        if user_id:
            # 非匿名用户添加用户的阅读历史
            cache_user.save_user_read_history(user_id, article_id)

            # 查询关注
            article['is_followed'] = cache_user.determine_user_follows_target(user_id, article['aut_id'])

            # 查询登录用户对文章的态度（点赞or不喜欢）
            ret = Attitude.query.options(load_only(Attitude.attitude))\
                .filter_by(user_id=user_id, article_id=article_id).first()
            if ret:
                article['attitude'] = ret.attitude

        # 更新阅读数
        cache_article.update_article_read_count(article_id)
        cache_user.update_user_article_read_count(article['aut_id'])

        # 获取相关文章推荐
        article['recomments'] = []
        similar_articles = self._feed_similar_articles(article_id)
        for _article_id in similar_articles:
            _article = cache_article.get_article_info(_article_id)
            article['recomments'].append({
                'art_id': _article['art_id'],
                'title': _article['title']
            })

        return article


class ArticleListResource(Resource):
    """
    文章列表数据
    """
    method_decorators = [validate_token_if_using]

    def _get_recommended_articles(self, channel_id, page, per_page):
        """
        获取推荐的文章（伪推荐）
        :param channel_id: 频道id
        :param page: 页数
        :param per_page: 每页数量
        :return: [article_id, ...]
        """
        offset = (page - 1) * per_page
        articles = Article.query.options(load_only()).filter_by(channel_id=channel_id, status=Article.STATUS.APPROVED)\
            .order_by(Article.id).offset(offset).limit(per_page).all()
        if articles:
            return [article.id for article in articles]
        else:
            return []

    def _feed_articles(self, channel_id, feed_count):
        """
        获取推荐文章
        :param channel_id: 频道id
        :param feed_count: 推荐数量
        :return: [{article_id, trace_params}, ...]
        """
        req = user_reco_pb2.User()

        if g.user_id:
            req.user_id = str(g.user_id)
        elif g.anonymous_id:
            req.user_id = str(g.anonymous_id)
        else:
            req.user_id = ''

        req.channel_id = channel_id
        req.article_num = feed_count

        stub = user_reco_pb2_grpc.UserRecommendStub(rpc_cli)
        resp = stub.user_recommend(req)

        # 曝光埋点参数
        trace_exposure = resp.exposure
        write_trace_log(trace_exposure)

        return resp.recommends

    def _generate_article_cover(self, article_id):
        """
        生成文章封面(处理测试数据专用）
        :param article_id: 文章id
        """
        article = Article.query.options(load_only(Article.cover)).filter_by(id=article_id).first()
        if article.cover['type'] > 0:
            return
        content = ArticleContent.query.filter_by(id=article_id).first()
        if content is None:
            return
        results = re.findall(r'src=\"http([^"]+)\"', content.content)
        length = len(results)
        if length <= 0:
            return
        elif length < 3:
            img_url = random.choice(results)
            img_url = 'http' + img_url
            Article.query.filter_by(id=article_id).update({'cover': {'type': 1, 'images': [img_url]}})
            db.session.commit()
        else:
            random.shuffle(results)
            img_urls = results[:3]
            img_urls = ['http'+img_url for img_url in img_urls]
            Article.query.filter_by(id=article_id).update({'cover': {'type': 3, 'images': img_urls}})
            db.session.commit()

    def get(self):
        """
        获取文章列表
        /v1_0/articles?channel_id&page&per_page
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('channel_id', type=parser.channel_id, required=True, location='args')
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ARTICLE_PER_PAGE_MIN,
                                                                 constants.DEFAULT_ARTICLE_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        channel_id = args.channel_id
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ARTICLE_PER_PAGE_MIN

        results = []

        if page == 1:
            # 第一页
            top_article_id_li = cache_article.get_channel_top_articles(channel_id)
            for article_id in top_article_id_li:
                article = cache_article.get_article_info(article_id)
                if article:
                    results.append(article)

        # 获取推荐文章列表
        # ret = self._get_recommended_articles(channel_id, page, per_page)
        # feed推荐 未使用page参数
        feeds = self._feed_articles(channel_id, per_page)

        # 查询文章
        for feed in feeds:
            # self._generate_article_cover(article_id)
            article = cache_article.get_article_info(feed.article_id)
            if article:
                article['trace'] = {
                    'click': feed.params.click,
                    'collect': feed.params.collect,
                    'share': feed.params.share,
                    'read': feed.params.read
                }
                results.append(article)

        return {'page': page, 'per_page': per_page, 'results': results}


class UserArticleListResource(Resource):
    """
    用户文章列表
    """
    def get(self, user_id):
        """
        获取user_id 用户的文章数据
        """
        exist = cache_user.determine_user_exists(user_id)
        if not exist:
            return {'message': 'Invalid request.'}, 400
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ARTICLE_PER_PAGE_MIN,
                                                                 constants.DEFAULT_ARTICLE_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ARTICLE_PER_PAGE_MIN

        results = []
        # articles = cache_user.get_user_articles(user_id)
        # total_count = len(articles)
        # page_articles = articles[(page - 1) * per_page:page * per_page]
        total_count, page_articles = cache_user.get_user_articles_by_page(user_id, page, per_page)

        for article_id in page_articles:
            article = cache_article.get_article_info(article_id)
            if article:
                results.append(article)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class CurrentUserArticleListResource(Resource):
    """
    当前用户的文章列表
    """
    method_decorators = [login_required]

    def get(self):
        """
        获取当前用户的文章列表
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ARTICLE_PER_PAGE_MIN,
                                                                 constants.DEFAULT_ARTICLE_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ARTICLE_PER_PAGE_MIN

        results = []
        # articles = cache_user.get_user_articles(g.user_id)
        # total_count = len(articles)
        # page_articles = articles[(page - 1) * per_page:page * per_page]
        total_count, page_articles = cache_user.get_user_articles_by_page(g.user_id, page, per_page)

        for article_id in page_articles:
            article = cache_article.get_article_info(article_id)
            if article:
                results.append(article)

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}

