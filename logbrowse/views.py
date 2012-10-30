# Create your views here.
def voltThrPlot(flight):
    return render_to_response('voltPlot.html',{'flight':flight})
