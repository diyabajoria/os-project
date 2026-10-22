def service_time(request, head, disk):
    return disk.overhead + disk.seek * abs(request.track - head) + request.size / disk.rate
