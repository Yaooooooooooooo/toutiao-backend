from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import g
from sqlalchemy.exc import IntegrityError


from utils.decorators import login_required
from models.user import Relation, User
from utils import parser
from models import db
from cache import user as cache_user


class BlacklistListResource(Resource):
    """
    用户拉黑
    """
    method_decorators = [login_required]

    def post(self):
        """
        拉黑用户
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.user_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        if target == g.user_id:
            return {'message': 'User cannot blacklist self.'}, 400
        try:
            blacklist = Relation(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.BLACKLIST)
            db.session.add(blacklist)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            # Change relation from DELETE to BLACKLIST
            ret = Relation.query.filter(Relation.user_id == g.user_id,
                                        Relation.target_user_id == target,
                                        Relation.relation == Relation.RELATION.DELETE) \
                .update({'relation': Relation.RELATION.BLACKLIST})
            if ret == 0:
                # Change relation from FOLLOW to BLACKLIST
                ret = Relation.query.filter(Relation.user_id == g.user_id,
                                            Relation.target_user_id == target,
                                            Relation.relation == Relation.RELATION.FOLLOW) \
                    .update({'relation': Relation.RELATION.BLACKLIST})

                if ret > 0:
                    cache_user.update_user_following_count(g.user_id, target, -1)

        db.session.commit()
        return {'target': target}, 201


class BlacklistResource(Resource):
    """
    用户拉黑
    """
    method_decorators = [login_required]

    def delete(self, target):
        """
        取消拉黑用户
        """
        Relation.query.filter_by(user_id=g.user_id, target_user_id=target, relation=Relation.RELATION.BLACKLIST)\
            .update({'relation': Relation.RELATION.DELETE})
        db.session.commit()
        return {'message': 'OK'}, 204

