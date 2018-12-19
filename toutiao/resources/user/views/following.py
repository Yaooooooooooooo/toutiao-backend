from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from flask import g
from flask_restful import inputs

from utils.decorators import login_required
from models.user import Relation
from utils import parser
from models import db
from cache import user as cache_user
from .. import constants


class FollowingListResource(Resource):
    """
    关注用户
    """
    method_decorators = [login_required]

    def post(self):
        """
        关注用户
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.user_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        if target == g.user_id:
            return {'message': 'User cannot follow self.'}, 400
        ret = 1
        try:
            follow = Relation(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.FOLLOW)
            db.session.add(follow)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            ret = Relation.query.filter(Relation.user_id == g.user_id,
                                        Relation.target_user_id == target,
                                        Relation.relation != Relation.RELATION.FOLLOW)\
                .update({'relation': Relation.RELATION.FOLLOW})
            db.session.commit()
        if ret > 0:
            cache_user.update_user_following(g.user_id, target)
        return {'target': target}, 201

    def get(self):
        """
        获取关注的用户列表
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN,
                                                                 constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_USER_FOLLOWINGS_PER_PAGE_MIN

        results = []
        followings = cache_user.get_user_followings(g.user_id)
        total_count = len(followings)
        for following_user_id in followings:
            user = cache_user.get_user(following_user_id)
            results.append(dict(
                id=following_user_id,
                name=user['name'],
                photo=user['photo'],
                fans_count=user['fans_count']
            ))

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class FollowingResource(Resource):
    """
    关注用户
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消关注用户
        """
        ret = Relation.query.filter(Relation.user_id == g.user_id,
                                    Relation.target_user_id == target,
                                    Relation.relation == Relation.RELATION.FOLLOW)\
            .update({'relation': Relation.RELATION.DELETE})
        db.session.commit()

        if ret > 0:
            cache_user.update_user_following(g.user_id, target, -1)
        return {'message': 'OK'}, 204


class FollowerListResource(Resource):
    """
    跟随用户列表（粉丝列表）
    """
    method_decorators = [login_required]

    def get(self):
        """
        获取粉丝列表
        """
        pass
