import time


def retry_on_error(max_attempts: int = 3, delay: float = 1.0):

    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

def truncate_float(value: float, decimals: int = 8) -> float:

    return float(f"{value:.{decimals}f}")

def get_current_timestamp() -> int:

    return int(time.time())