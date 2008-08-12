#!/usr/bin/python
#
# Copyright 2008 Google Inc. All Rights Reserved.

"""Tests for action_common."""

import unittest, os, sys, tempfile, StringIO, copy

import common
from autotest_lib.cli import cli_mock, topic_common, action_common, rpc
from autotest_lib.frontend.afe.json_rpc import proxy

#
# List action
#
class atest_list_unittest(cli_mock.cli_unittest):
    def test_check_for_wilcard_none(self):
        orig_filters = {'name__in': ['item0', 'item1']}
        orig_checks = {'name__in': ['item0', 'item1']}
        mytest = action_common.atest_list()

        filters = copy.deepcopy(orig_filters)
        checks = copy.deepcopy(orig_checks)
        mytest.check_for_wildcard(filters, checks)
        self.assertEqual(filters, orig_filters)
        self.assertEqual(checks, orig_checks)


    def test_check_for_wilcard_none_list(self):
        orig_filters = {'name__in': ['item0']}
        orig_checks = {'name__in': ['item0']}
        mytest = action_common.atest_list()

        filters = copy.deepcopy(orig_filters)
        checks = copy.deepcopy(orig_checks)
        mytest.check_for_wildcard(filters, checks)
        self.assertEqual(filters, orig_filters)
        self.assertEqual(checks, orig_checks)

    def test_check_for_wilcard_one_list(self):
        filters = {'something__in': ['item*']}
        checks = {'something__in': ['item*']}
        mytest = action_common.atest_list()

        mytest.check_for_wildcard(filters, checks)
        self.assertEqual(filters, {'something__startswith': 'item'})
        self.assertEqual(checks, {'something__startswith': None})


    def test_check_for_wilcard_one_string(self):
        filters = {'something__name': 'item*'}
        checks = {'something__name': 'item*'}
        mytest = action_common.atest_list()

        mytest.check_for_wildcard(filters, checks)
        self.assertEqual(filters, {'something__name__startswith': 'item'})
        self.assertEqual(checks, {'something__name__startswith': None})



    def test_check_for_wilcard_one_string_login(self):
        filters = {'something__login': 'item*'}
        checks = {'something__login': 'item*'}
        mytest = action_common.atest_list()

        mytest.check_for_wildcard(filters, checks)
        self.assertEqual(filters, {'something__login__startswith': 'item'})
        self.assertEqual(checks, {'something__login__startswith': None})


    def test_check_for_wilcard_two(self):
        orig_filters = {'something__in': ['item0*', 'item1*']}
        orig_checks = {'something__in': ['item0*', 'item1*']}
        mytest = action_common.atest_list()

        filters = copy.deepcopy(orig_filters)
        checks = copy.deepcopy(orig_checks)
        self.god.stub_function(sys, 'exit')
        sys.exit.expect_call(1).and_raises(cli_mock.ExitException)
        self.god.mock_io()
        self.assertRaises(cli_mock.ExitException,
                          mytest.check_for_wildcard, filters, checks)
        (out, err) = self.god.unmock_io()
        self.god.check_playback()
        self.assertEqual(filters, orig_filters)
        self.assertEqual(checks, orig_checks)


    def _atest_list_execute(self, filters={}, check_results={}):
        values = [{u'id': 180,
                   u'platform': 0,
                   u'name': u'label0',
                   u'invalid': 0,
                   u'kernel_config': u''},
                  {u'id': 338,
                   u'platform': 0,
                   u'name': u'label1',
                   u'invalid': 0,
                   u'kernel_config': u''}]
        mytest = action_common.atest_list()
        mytest.afe = rpc.afe_comm()
        self.mock_rpcs([('get_labels',
                         filters,
                         True,
                         values)])
        self.god.mock_io()
        self.assertEqual(values,
                         mytest.execute(op='get_labels',
                                        filters=filters,
                                        check_results=check_results))
        (out, err) = self.god.unmock_io()
        self.god.check_playback()
        return (out, err)


    def test_atest_list_execute_no_filters(self):
        self._atest_list_execute()


    def test_atest_list_execute_filters_all_good(self):
        filters = {}
        check_results = {}
        filters['name__in'] = ['label0', 'label1']
        check_results['name__in'] = 'name'
        (out, err) = self._atest_list_execute(filters, check_results)
        self.assertEqual(err, '')


    def test_atest_list_execute_filters_good_and_bad(self):
        filters = {}
        check_results = {}
        filters['name__in'] = ['label0', 'label1', 'label2']
        check_results['name__in'] = 'name'
        (out, err) = self._atest_list_execute(filters, check_results)
        self.assertWords(err, ['Unknown', 'label2'])


    def test_atest_list_execute_items_good_and_bad_no_check(self):
        filters = {}
        check_results = {}
        filters['name__in'] = ['label0', 'label1', 'label2']
        check_results['name__in'] = None
        (out, err) = self._atest_list_execute(filters, check_results)
        self.assertEqual(err, '')


    def test_atest_list_execute_filters_wildcard(self):
        filters = {}
        check_results = {}
        filters['name__in'] = ['label*']
        check_results['name__in'] = 'name'
        values = [{u'id': 180,
                   u'platform': 0,
                   u'name': u'label0',
                   u'invalid': 0,
                   u'kernel_config': u''},
                  {u'id': 338,
                   u'platform': 0,
                   u'name': u'label1',
                   u'invalid': 0,
                   u'kernel_config': u''}]
        mytest = action_common.atest_list()
        mytest.afe = rpc.afe_comm()
        self.mock_rpcs([('get_labels', {'name__startswith': 'label'},
                         True, values)])
        self.god.mock_io()
        self.assertEqual(values,
                         mytest.execute(op='get_labels',
                                        filters=filters,
                                        check_results=check_results))
        (out, err) = self.god.unmock_io()
        self.god.check_playback()
        self.assertEqual(err, '')



#
# Creation & Deletion of a topic (ACL, label, user)
#
class atest_create_or_delete_unittest(cli_mock.cli_unittest):
    def _create_cr_del(self, items):
        def _items():
            return items
        crdel = action_common.atest_create_or_delete()
        crdel.afe = rpc.afe_comm()

        crdel.topic =  crdel.usage_topic = 'label'
        crdel.op_action = 'add'
        crdel.get_items = _items
        crdel.data['platform'] = False
        crdel.data_item_key = 'name'
        return crdel


    def test_execute_create_one_topic(self):
        acr = self._create_cr_del(['label0'])
        self.mock_rpcs([('add_label',
                         {'name': 'label0', 'platform': False},
                         True, 42)])
        ret = acr.execute()
        self.assert_(['label0'], ret)


    def test_execute_create_two_topics(self):
        acr = self._create_cr_del(['label0', 'label1'])
        self.mock_rpcs([('add_label',
                         {'name': 'label0', 'platform': False},
                         True, 42),
                        ('add_label',
                         {'name': 'label1', 'platform': False},
                         True, 43)])
        ret = acr.execute()
        self.assertEqualNoOrder(['label0', 'label1'], ret)


    def test_execute_create_error(self):
        acr = self._create_cr_del(['label0'])
        self.mock_rpcs([('add_label',
                         {'name': 'label0', 'platform': False},
                         False,
                         '''ValidationError:
                         {'name': 'This value must be unique (label0)'}''')])
        ret = acr.execute()
        self.assertEqualNoOrder([], ret)


    def test_execute_create_error_dup(self):
        acr = self._create_cr_del(['label0'])
        self.mock_rpcs([('add_label',
                         {'name': 'label0', 'platform': False},
                         True, 42),
                        ('add_label',
                         {'name': 'label0', 'platform': False},
                         False,
                         '''ValidationError:
                         {'name': 'This value must be unique (label0)'}''')])
        ret = acr.execute()
        self.assertEqualNoOrder(['label0'], ret)



#
# Adding or Removing users or hosts from a topic(ACL or label)
#
class atest_add_or_remove_unittest(cli_mock.cli_unittest):
    def _create_add_remove(self, items, users=None, hosts=None):
        def _items():
            return [items]
        addrm = action_common.atest_add_or_remove()
        addrm.afe = rpc.afe_comm()
        if users:
            addrm.users = users
        if hosts:
            addrm.hosts = hosts

        addrm.topic = 'acl_group'
        addrm.usage_topic = 'ACL'
        addrm.op_action = 'add'
        addrm.get_items = _items
        return addrm


    def test__add_remove_uh_to_topic(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         True,
                         None)])
        acl_addrm._add_remove_uh_to_topic('acl0', 'users')


    def test__add_remove_uh_to_topic_raise(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'])
        self.assertRaises(AttributeError,
                          acl_addrm._add_remove_uh_to_topic,
                          'acl0', 'hosts')


    def test_execute_add_or_remove_uh_to_topic_acl_users(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         True,
                         None)])
        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqualNoOrder(['acl0'], users_ok)
        self.assertEqual([], hosts_ok)



    def test_execute_add_or_remove_uh_to_topic_acl_users_hosts(self):
        acl_addrm = self._create_add_remove('acl0',
                                            users=['user0', 'user1'],
                                            hosts=['host0', 'host1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         True,
                         None),
                        ('acl_group_add_hosts',
                         {'id': 'acl0',
                          'hosts': ['host0', 'host1']},
                         True,
                         None)])
        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqualNoOrder(['acl0'], users_ok)
        self.assertEqualNoOrder(['acl0'], hosts_ok)
        self.god.check_playback()


    def test_execute_add_or_remove_uh_to_topic_acl_bad_users(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         False,
                         'DoesNotExist: User matching query does not exist.')])
        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqual([], users_ok)
        self.assertEqual([], hosts_ok)
        self.assertOutput(acl_addrm,
                          err_words_ok=['DoesNotExist', 'acl0',
                                        'acl_group_add_users',
                                        'user0', 'user1'],
                          err_words_no = ['acl_group_add_hosts'])


    def test_execute_add_or_remove_uh_to_topic_acl_bad_users_good_hosts(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'],
                                        hosts=['host0', 'host1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         False,
                         'DoesNotExist: User matching query does not exist.'),
                        ('acl_group_add_hosts',
                         {'id': 'acl0',
                          'hosts': ['host0', 'host1']},
                         True,
                         None)])

        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqual([], users_ok)
        self.assertEqual(['acl0'], hosts_ok)
        self.assertOutput(acl_addrm,
                          err_words_ok=['DoesNotExist', 'acl0',
                                        'acl_group_add_users',
                                        'user0', 'user1'],
                          err_words_no = ['acl_group_add_hosts'])


    def test_execute_add_or_remove_uh_to_topic_acl_good_users_bad_hosts(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'],
                                        hosts=['host0', 'host1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         True,
                         None),
                        ('acl_group_add_hosts',
                         {'id': 'acl0',
                          'hosts': ['host0', 'host1']},
                         False,
                         'DoesNotExist: Host matching query does not exist.')])

        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqual(['acl0'], users_ok)
        self.assertEqual([], hosts_ok)
        self.assertOutput(acl_addrm,
                          err_words_ok=['DoesNotExist', 'acl0',
                                        'acl_group_add_hosts',
                                        'host0', 'host1'],
                          err_words_no = ['acl_group_add_users'])


    def test_execute_add_or_remove_uh_to_topic_acl_bad_users_bad_hosts(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'],
                                        hosts=['host0', 'host1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         False,
                         'DoesNotExist: User matching query does not exist.'),
                        ('acl_group_add_hosts',
                         {'id': 'acl0',
                          'hosts': ['host0', 'host1']},
                         False,
                         'DoesNotExist: Host matching query does not exist.')])

        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqual([], users_ok)
        self.assertEqual([], hosts_ok)
        self.assertOutput(acl_addrm,
                          err_words_ok=['DoesNotExist', 'acl0',
                                        'acl_group_add_hosts',
                                        'host0', 'host1',
                                        'acl_group_add_users',
                                        'user0', 'user1'])


    def test_execute_add_or_remove_to_topic_bad_acl_uh(self):
        acl_addrm = self._create_add_remove('acl0',
                                        users=['user0', 'user1'],
                                        hosts=['host0', 'host1'])
        self.mock_rpcs([('acl_group_add_users',
                         {'id': 'acl0',
                          'users': ['user0', 'user1']},
                         False,
                         'DoesNotExist: acl_group matching '
                         'query does not exist.'),
                        ('acl_group_add_hosts',
                         {'id': 'acl0',
                          'hosts': ['host0', 'host1']},
                         False,
                         'DoesNotExist: acl_group matching '
                         'query does not exist.')])
        (users_ok, hosts_ok) = acl_addrm.execute()
        self.assertEqual([], users_ok)
        self.assertEqual([], hosts_ok)
        self.assertOutput(acl_addrm,
                          err_words_ok=['DoesNotExist', 'acl0',
                                        'acl_group_add_hosts', 'host0',
                                        'host1', 'acl_group_add_users',
                                        'user0', 'user1'])




if __name__ == '__main__':
    unittest.main()