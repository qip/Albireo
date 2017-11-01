from utils.SessionManager import SessionManager
from utils.db import row2dict
from utils.http import json_resp, rpc_request
from utils.exceptions import ClientError
from domain.WebHook import WebHook
from domain.WebHookToken import WebHookToken
from domain.Favorites import Favorites
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import desc
from sqlalchemy.orm.exc import NoResultFound


# noinspection PyMethodMayBeStatic
class WebHookService:

    def __init__(self):
        pass

    def __process_user_obj_in_web_hook(self, web_hook, web_hook_dict):
        if web_hook.created_by is not None:
            web_hook_dict['created_by'] = row2dict(web_hook.created_by)
            web_hook_dict['created_by'].pop('password', None)
        web_hook_dict.pop('created_by_uid', None)

    def list_web_hook(self):
        session = SessionManager.Session()
        try:
            web_hook_list = session.query(WebHook).\
                options(joinedload(WebHook.created_by)).\
                order_by(desc(getattr(WebHook, 'register_time'))).\
                all()
            web_hook_dict_list = []

            for web_hook in web_hook_list:
                web_hook_dict = row2dict(web_hook)
                self.__process_user_obj_in_web_hook(web_hook, web_hook_dict)
                web_hook_dict_list.append(web_hook_dict)

            return json_resp({
                'data': web_hook_dict_list,
                'total': len(web_hook_list)
            })
        finally:
            SessionManager.Session.remove()

    def register_web_hook(self, web_hook_dict, add_by_uid):
        """
        register an web hook and send an initial keep alive event
        :param web_hook_dict:
        :param add_by_uid:
        :return:
        """
        session = SessionManager.Session()
        try:
            web_hook = WebHook(name=web_hook_dict.get('name'),
                               description=web_hook_dict.get('description'),
                               url=web_hook_dict.get('url'),
                               created_by_uid=add_by_uid)
            session.add(web_hook)
            session.commit()
            web_hook_id = str(web_hook.id)

            # send event via rpc
            rpc_request.send('initialize_web_hook', {'web_hook_id': web_hook_id, 'web_hook_url': web_hook.url})

            return json_resp({'data': web_hook_id})
        finally:
            SessionManager.Session.remove()

    def update_web_hook(self, web_hook_id, web_hook_dict):
        """
        update a web hook
        :param web_hook_dict:
        :param web_hook_id:
        :return:
        """
        session = SessionManager.Session()
        try:
            web_hook = session.query(WebHook).\
                filter(WebHook.id == web_hook_id).\
                one()
            web_hook.name = web_hook_dict.get('name')
            web_hook.description = web_hook_dict.get('description')
            web_hook.url = web_hook_dict.get('url')
            web_hook.status = web_hook_dict.get('status')
            web_hook.consecutive_failure_count = web_hook_dict.get('consecutive_failure_count')

            session.commit()

            return json_resp({'message': 'ok'})
        finally:
            SessionManager.Session.remove()

    def delete_web_hook(self, web_hook_id):
        """
        delete a web hook, this will also delete all web hook token with this web hook id
        :param web_hook_id:
        :return:
        """
        session = SessionManager.Session()
        try:
            token_list = session.query(WebHookToken).\
                filter(WebHookToken.web_hook_id == web_hook_id).\
                all()
            for web_hook_token in token_list:
                session.delete(web_hook_token)
            web_hook = session.query(WebHook).\
                filter(WebHook.id == web_hook_id).\
                one()
            session.delete(web_hook)
            session.commit()
            return json_resp({'message': 'ok'})
        finally:
            SessionManager.Session.remove()

    def revive(self, web_hook_id, token_id_list):
        session = SessionManager.Session()
        try:
            fav_dict_list = []
            if len(token_id_list) > 0:
                web_hook_token_list = session.query(WebHookToken).\
                    filter(WebHookToken.web_hook_id == web_hook_id).\
                    filter(WebHookToken.token_id.in_(token_id_list)).\
                    all()

                user_id_list = [web_hook.user_id for web_hook in web_hook_token_list]

                favorites_list = session.query(Favorites).\
                    filter(Favorites.user_id.in_(user_id_list)).\
                    group_by(Favorites.user_id, Favorites.id).\
                    all()

                for favorite in favorites_list:
                    fav_dict = row2dict(favorite)
                    for web_hook in web_hook_token_list:
                        if fav_dict['user_id'] == web_hook.user_id:
                            fav_dict['token_id'] = web_hook.token_id
                            break
                    fav_dict.pop('user_id', None)
                    fav_dict_list.append(fav_dict)

            # somehow sqlalchemy change the dict after commit, so we need dump the data before commit
            resp_data = json_resp({'data': fav_dict_list})

            # reset its status
            web_hook = session.query(WebHook).\
                filter(WebHook.id == web_hook_id).\
                one()

            web_hook.status = WebHook.STATUS_IS_ALIVE
            session.commit()

            return resp_data
        except NoResultFound:
            raise ClientError(ClientError.NOT_FOUND, 404)
        finally:
            SessionManager.Session()

    def list_web_hook_by_user(self, user_id):
        session = SessionManager.Session()
        try:
            web_hook_token_list = session.query(WebHookToken).\
                options(joinedload(WebHookToken.web_hook)).\
                filter(WebHookToken.user_id == user_id).\
                all()

            return json_resp({
                'data': [row2dict(web_hook_token.web_hook) for web_hook_token in web_hook_token_list],
                'total': len(web_hook_token_list)
            })
        finally:
            SessionManager.Session.remove()

    def add_web_hook_token(self, token_id, web_hook_id, user_id):
        session = SessionManager.Session()
        try:
            web_hook = session.query(WebHook).filter(WebHook.id == web_hook_id).one()
            web_hook_token = WebHookToken(web_hook_id=web_hook_id,
                                          user_id=user_id,
                                          token_id=token_id)
            session.add(web_hook_token)
            session.commit()
            return json_resp({'message': 'ok'})
        except NoResultFound:
            raise ClientError('web hook not existed')
        finally:
            SessionManager.Session.remove()

    def delete_web_hook_token(self, web_hook_id, user_id):
        session = SessionManager.Session()
        try:
            web_hook_token = session.query(WebHookToken).\
                filter(WebHookToken.web_hook_id == web_hook_id).\
                filter(WebHookToken.user_id == user_id).\
                one()

            session.delete(web_hook_token)
            session.commit()
            return json_resp({'message': 'ok'})
        except NoResultFound:
            raise ClientError(ClientError.NOT_FOUND, 404)
        finally:
            SessionManager.Session.remove()


web_hook_service = WebHookService()