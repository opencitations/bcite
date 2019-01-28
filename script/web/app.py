import web , re , requests , string , urllib , time , datetime, json, csv
import urllib.parse
from web import form
from script.ramose.ramose import APIManager
from io import StringIO

web.config.debug = False

# routing
urls = (
	'/','index',
    '/results', 'results',
    "(/api/.+)", "Api",
)

# templates
render = web.template.render('templates/', base="layout", globals={'re':re})

coci_api_manager = APIManager(["v1.hf"])

class Api:
    def GET(self, call):
        status_code, res = coci_api_manager.exec_op(call)
        if status_code == 200:
            web.header('Access-Control-Allow-Origin', '*')
            web.header('Access-Control-Allow-Credentials', 'true')
            web.header('Content-Type', "application/json")
            return res
        else:
            with StringIO(res) as f:
                mes = json.dumps(next(csv.DictReader(f)), ensure_ascii=False)
                raise web.HTTPError(
                    str(status_code), {"Content-Type": "application/json"}, mes)


myform = form.Form( 
    form.Textarea('author', form.notnull , form.regexp(r'((.*),(.*))', 'Must be: Lastname, Name; Lastname, Name'), value="", description='author', post='<a class="tip" href="#" data-toggle="tooltip" data-placement="right" title="e.g. Berners-Lee, Tim; Hendler, James; Lassila, Ora"><i class="fas fa-info-circle"></i></a>'),  
    form.Textarea('title', form.notnull),
    form.Textbox('journal'),
    form.Textbox('volume'),
    form.Textbox('issue'),
    form.Textbox('year'),
    form.Textbox('publisher'),
	#form.Textbox("ORCID", form.regexp(r'^http[s]?:\/\/orcid.org\/(\d{4})-(\d{4})-(\d{4})-(\d{3}[0-9X])$', 'Must be a ORCID'), description='ORCID', post='<a class="tip" href="#" data-toggle="tooltip" data-placement="right" title="The data provider\'s ORCID"><i class="fas fa-info-circle"></i></a>'), #regex suggested by pkp (ojs)
    form.Textbox("DOI", form.notnull, form.regexp(r'^10.\d{4,9}\/[-._;()/:a-zA-Z0-9]+$', 'Must be a DOI')), #regex suggested by crossref
    form.Textarea('references', form.notnull , post='<em>paste your references here - each paragraph corresponds to a single reference entry.</em>'),
    form.Dropdown('style', ['Chicago', 'MLA'], form.notnull),
    form.Button("form_action", value='search' , description='search', type="submit")
    ) 

f = myform() 

class index: 
    def GET(self): 
        return render.index(f, results=None)


    def POST(self): 
        data = web.input()
        ts = time.time()

        if f.validates():
            citingEntity = {} # build json
            if ';' in data.author:
                authors = data.author.split(';')
            else:
                authors = [data.author]
            citingEntity['author'] = authors
            citingEntity['title'] = data.title
            if data.journal != '':
                citingEntity['journal'] = data.journal
            if data.volume != '':
                citingEntity['volume'] = data.volume
            if data.issue != '':
                citingEntity['issue'] = data.issue
            citingEntity['year'] = data.year
            citingEntity['publisher'] = data.publisher
            citingEntity['doi'] = data.DOI
            citingEntityEncoded = json.dumps(citingEntity)
            # /citing/{timestamp}/{json}
            request = requests.get('http://localhost:8000/api/citing/'+str(ts)+'/'+urllib.parse.quote( citingEntityEncoded ))
            response = json.loads(request.text)
            idCitingRef = response[0]['id']
            raise web.seeother('/results?idRef='+idCitingRef+'&references='+urllib.parse.quote((web.input().references))+'&style='+web.input().style+'&time='+str(ts))
        
        else:
            return render.index(f, results=None)
class results:
    def GET(self):
        s = str(web.ctx.query)
        referencesDecoded = urllib.parse.unquote(web.input().references)
        timeStamp = s.split("time=", 1)[1]
        splitReferencesText = [x for x in referencesDecoded.split('\n') if x != '\r' and x != '\n' and x != ''] # extract references from 'references' 
        splitReferences = [s.replace('\r', '') for s in splitReferencesText]
        results = []        
        for referenceText in splitReferences:
           # /reference/{timestamp}/{citing}/{style}/{reference}
            request = requests.get('http://localhost:8000/api/reference/'+str(web.input().time)+'/'+web.input().idRef+'/'+web.input().style+'/'+urllib.parse.quote(referenceText) )
            request.encoding = "UTF-8"
            response = request.json()
            referenceMatch = {}
            referenceMatch['submitted'] = referenceText
            referenceMatch['match'] = response[0]['reference']
            referenceMatch['id'] = response[0]['id']
            results.append(referenceMatch)
        return render.results(results=results, content='Placeholder for the citing entity')

if __name__ == "__main__":
	app = web.application(urls, globals())
	app.internalerror = web.debugerror
	app.run()