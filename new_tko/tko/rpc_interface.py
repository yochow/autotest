import re, datetime
from django.db import models as dbmodels
from autotest_lib.frontend import thread_local
from autotest_lib.frontend.afe import rpc_utils, model_logic
from autotest_lib.new_tko.tko import models, tko_rpc_utils

# table/spreadsheet view support

def get_test_views(**filter_data):
    return rpc_utils.prepare_for_serialization(
        models.TestView.list_objects(filter_data))


def get_num_test_views(**filter_data):
    return models.TestView.query_count(filter_data)


def get_group_counts(group_by, header_groups=[], extra_select_fields=[],
                     **filter_data):
    """
    Queries against TestView grouping by the specified fields and computings
    counts for each group.
    * group_by should be a list of field names.
    * extra_select_fields can be used to specify additional fields to select
      (usually for aggregate functions).
    * header_groups can be used to get lists of unique combinations of group
      fields.  It should be a list of tuples of fields from group_by.  It's
      primarily for use by the spreadsheet view.

    Returns a dictionary with two keys:
    * header_values contains a list of lists, one for each header group in
      header_groups.  Each list contains all the values for the corresponding
      header group as tuples.
    * groups contains a list of dicts, one for each row.  Each dict contains
      keys for each of the group_by fields, plus a 'group_count' key for the
      total count in the group, plus keys for each of the extra_select_fields.
      The keys for the extra_select_fields are determined by the "AS" alias of
      the field.
    """
    group_by = list(set(group_by)) # eliminate duplicates

    query = models.TestView.query_objects(filter_data)
    counts = models.TestView.objects.get_group_counts(query, group_by,
                                                      extra_select_fields)
    if len(counts) > tko_rpc_utils.MAX_GROUP_RESULTS:
        raise tko_rpc_utils.TooManyRowsError(
            'Query yielded %d rows, exceeding maximum %d' % (
            len(counts), tko_rpc_utils.MAX_GROUP_RESULTS))

    extra_field_names = [sql.lower().rsplit(' as ', 1)[1]
                         for sql in extra_select_fields]
    group_processor = tko_rpc_utils.GroupDataProcessor(group_by, header_groups,
                                                       extra_field_names)
    group_dicts = [group_processor.get_group_dict(count_row)
                   for count_row in counts]

    header_values = group_processor.get_sorted_header_values()
    if header_groups:
        for group_dict in group_dicts:
            group_processor.replace_headers_with_indices(group_dict)

    result = {'header_values' : header_values,
              'groups' : group_dicts}
    return rpc_utils.prepare_for_serialization(result)


def get_num_groups(group_by, **filter_data):
    """
    Gets the count of unique groups with the given grouping fields.
    """
    query = models.TestView.query_objects(filter_data)
    return models.TestView.objects.get_num_groups(query, group_by)


# SQL expression to compute passed test count for test groups
_PASS_COUNT_SQL = 'SUM(IF(status="GOOD", 1, 0)) AS pass_count'
_COMPLETE_COUNT_SQL = ('SUM(IF(NOT (status="TEST_NA" OR '
                                   'status="RUNNING" OR '
                                   'status="NOSTATUS"), 1, 0)) '
                       'AS complete_count')
_INCOMPLETE_COUNT_SQL = ('SUM(IF(status="RUNNING", 1, 0)) '
                         'AS incomplete_count')

def get_status_counts(group_by, header_groups=[], **filter_data):
    """
    Like get_group_counts, but also computes counts of passed, complete (and
    valid), and incomplete tests, stored in keys "pass_count', 'complete_count',
    and 'incomplete_count', respectively.
    """
    extra_fields = [_PASS_COUNT_SQL, _COMPLETE_COUNT_SQL, _INCOMPLETE_COUNT_SQL]
    return get_group_counts(group_by, extra_select_fields=extra_fields,
                            header_groups=header_groups, **filter_data)


def get_test_logs_urls(**filter_data):
    """
    Return URLs to test logs for all tests matching the filter data.
    """
    query = models.TestView.query_objects(filter_data)
    tests = set((test_view.job_tag, test_view.test) for test_view in query)
    links = []
    for job_tag, test in tests:
        links.append('/results/' + job_tag + '/' + test)
    return links


def get_job_ids(**filter_data):
    """
    Returns AFE job IDs for all tests matching the filters.
    """
    query = models.TestView.query_objects(filter_data)
    job_ids = set()
    for test_view in query.values('job_tag').distinct():
        # extract job ID from tag
        job_ids.add(int(test_view['job_tag'].split('-')[0]))
    return list(job_ids)


# graphing view support

def get_hosts_and_tests():
    """\
    Gets every host that has had a benchmark run on it. Additionally, also
    gets a dictionary mapping the host names to the benchmarks.
    """

    host_info = {}
    q = (dbmodels.Q(test_name__startswith='kernbench') |
         dbmodels.Q(test_name__startswith='dbench') |
         dbmodels.Q(test_name__startswith='tbench') |
         dbmodels.Q(test_name__startswith='unixbench') |
         dbmodels.Q(test_name__startswith='iozone'))
    test_query = models.TestView.objects.filter(q).values(
        'test_name', 'hostname', 'machine_idx').distinct()
    for result_dict in test_query:
        hostname = result_dict['hostname']
        test = result_dict['test_name']
        machine_idx = result_dict['machine_idx']
        host_info.setdefault(hostname, {})
        host_info[hostname].setdefault('tests', [])
        host_info[hostname]['tests'].append(test)
        host_info[hostname]['id'] = machine_idx
    return rpc_utils.prepare_for_serialization(host_info)


# test label management

def add_test_label(name, description=None):
    return models.TestLabel.add_object(name=name, description=description).id


def modify_test_label(label_id, **data):
    models.TestLabel.smart_get(label_id).update_object(data)


def delete_test_label(label_id):
    models.TestLabel.smart_get(label_id).delete()


def get_test_labels(**filter_data):
    return rpc_utils.prepare_for_serialization(
        models.TestLabel.list_objects(filter_data))


def get_test_labels_for_tests(**test_filter_data):
    tests = models.Test.objects.query_using_test_view(test_filter_data)
    labels = models.TestLabel.list_objects({'tests__in' : tests})
    return rpc_utils.prepare_for_serialization(labels)


def test_label_add_tests(label_id, **test_filter_data):
    print label_id
    test_objs = models.Test.objects.query_using_test_view(test_filter_data)
    models.TestLabel.smart_get(label_id).tests.add(*test_objs)


def test_label_remove_tests(label_id, **test_filter_data):
    test_objs = models.Test.objects.query_using_test_view(test_filter_data)
    models.TestLabel.smart_get(label_id).tests.remove(*test_objs)


# saved queries

def get_saved_queries(**filter_data):
    return rpc_utils.prepare_for_serialization(
        models.SavedQuery.list_objects(filter_data))


def add_saved_query(name, url_token):
    name = name.strip()
    owner = thread_local.get_user()
    existing_list = list(models.SavedQuery.objects.filter(owner=owner,
                                                          name=name))
    if existing_list:
        query_object = existing_list[0]
        query_object.url_token = url_token
        query_object.save()
        return query_object.id

    return models.SavedQuery.add_object(owner=owner, name=name,
                                        url_token=url_token).id


def delete_saved_queries(id_list):
    user = thread_local.get_user()
    query = models.SavedQuery.objects.filter(id__in=id_list, owner=user)
    if query.count() == 0:
        raise model_logic.ValidationError('No such queries found for this user')
    query.delete()


# other

_benchmark_key = {
    'kernbench' : 'elapsed',
    'dbench' : 'throughput',
    'tbench' : 'throughput',
    'unixbench' : 'score',
    'iozone' : '32768-4096-fwrite'
}


def get_static_data():
    result = {}
    group_fields = []
    for field in models.TestView.group_fields:
        if field in models.TestView.extra_fields:
            name = models.TestView.extra_fields[field]
        else:
            name = models.TestView.get_field_dict()[field].verbose_name
        group_fields.append((name.capitalize(), field))
    model_fields = [(field.verbose_name.capitalize(), field.column)
                    for field in models.TestView._meta.fields]
    extra_fields = [(field_name.capitalize(), field_sql)
                    for field_sql, field_name
                    in models.TestView.extra_fields.iteritems()]

    result['group_fields'] = sorted(group_fields)
    result['all_fields'] = sorted(model_fields + extra_fields)
    result['test_labels'] = get_test_labels(sort_by=['name'])
    result['user_login'] = thread_local.get_user()
    result['benchmark_key'] = _benchmark_key
    return result