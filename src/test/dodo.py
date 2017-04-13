def task_start_redis():
    """Start Redis in docker"""
    return {'actions': ['sudo docker start mail2alert-redis']}


def task_stop_redis():
    """Start Redis in docker"""
    return {'actions': ['sudo docker stop mail2alert-redis']}


def task_redis_tests():
    pass


def task_it_tests():
    pass


def task_config_tests():
    pass
