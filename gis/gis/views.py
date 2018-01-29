from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from .settings import MEDIA_ROOT

from . import main
from django.utils.encoding import smart_str

def index(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        # store file with a route
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        # call script to process, arguments: received route file, exported kml file with all roads
        #return HttpResponse(MEDIA_ROOT + '\\' + filename + "  " + MEDIA_ROOT + '\croatia.kml')

        processed_file_url, processed_file_name = main.start_process(MEDIA_ROOT + '\\' + filename, MEDIA_ROOT + '\croatia.kml', MEDIA_ROOT)
        # processed_file_url = fs.url(processed_file)
        with open(processed_file_url, 'r') as f:
            response = HttpResponse(f.read(),
                content_type='application/force-download')  # mimetype is replaced by content_type for django 1.7
            response['Content-Disposition'] = 'attachment; filename=%s' % processed_file_name
            response['X-Sendfile'] = processed_file_url
            return response

    return render(request, 'gis/simple_upload.html')

