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

class DinamycForm(form.Form):
    """dynamic form"""
    def add_input(self, new_input):
        list_inputs = list(self.inputs)
        list_inputs.insert( (len(list_inputs) -1), new_input)
        self.inputs = tuple(list_inputs)

authorForm = DinamycForm(
    form.Textbox('author', form.notnull , form.regexp(r'((.*),(.*))', 'Must be: Lastname, Name'), description='author', post='<a class="tip" href="#" data-toggle="tooltip" data-placement="right" title="e.g. Berners-Lee, Tim"><i class="fas fa-info-circle"></i></a>'),
    form.Button("form_action", value='add' , description='add', type="submit")
    )

myform = form.Form( 
    form.Textbox('title', form.notnull),
    form.Textbox('journal'),
    form.Textbox('volume'),
    form.Textbox('issue'),
    form.Textbox('year', form.notnull),
    form.Textbox('publisher', form.notnull),
	# form.Textbox("ORCID", form.notnull,
	# 	form.regexp(r'^http[s]?:\/\/orcid.org\/(\d{4})-(\d{4})-(\d{4})-(\d{3}[0-9X])$', 'Must be a ORCID')), #regex suggested by pkp (ojs)
    form.Textbox("DOI", form.notnull,
        form.regexp(r'^10.\d{4,9}\/[-._;()/:a-zA-Z0-9]+$', 'Must be a DOI')), #regex suggested by crossref
    form.Textarea('references', form.notnull , post='<em>paste your references here - each paragraph corresponds to a single reference entry.</em>'),
    form.Dropdown('style', ['Chicago', 'MLA'], form.notnull),
    form.Button("form_action", value='search' , description='search', type="submit")
    ) 

f = myform() 
authorform = authorForm()  

class index: 
    def GET(self): 
        return render.index(authorform, f, results=None)


    def POST(self): 
        data = web.input()
        i = web.input(form_action='add')
        s = web.input(form_action='search')
        ts = time.time()

        if (i.form_action == 'add') and authorform.validates():
            authorform.add_input(web.form.Textbox('author',form.notnull , form.regexp(r'((.*),(.*))', 'Must be in the form: Lastname, Name') )) 
            return render.index(authorForm=authorform, form=f, results=None)
        elif (i.form_action == 'add') and not authorform.validates():
            return render.index(authorForm=authorform, form=f, results=None)
        elif (s.form_action == 'search') and (not authorform.validates() or not f.validates()):
            return render.index(authorForm=authorform, form=f, results=None)
        elif (s.form_action == 'search') and f.validates() and authorform.validates():
            citingEntity = {} # build json
            dataAu = web.input(author=[])
            authors = dataAu.author 
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
            ##################### first call to BCite API: send metadata about the citing entity and get back an ID
            # /citing/{timestamp}/{json}
            request = requests.get('http://localhost:8000/api/citing/'+str(ts)+'/'+urllib.parse.quote(str(citingEntityEncoded)))
            response = json.loads(request.text)
            idCitingRef = response[0]['id']
            raise web.seeother('/results?idRef='+idCitingRef+'&references='+urllib.parse.quote((web.input().references))+'&style='+web.input().style+'&time='+str(ts))
            ##################### remove the following line
            # raise web.seeother('/results?references='+urllib.parse.quote((web.input().references))+'&style='+web.input().style+'&time='+str(ts))

class results:
    def GET(self):
        s = str(web.ctx.query)
        referencesDecoded = urllib.parse.unquote(web.input().references)
        timeStamp = s.split("time=", 1)[1]
        splitReferencesText = [x for x in referencesDecoded.split('\n') if x != '\r'] # extract references from 'references' 
        results = []        
        for referenceText in splitReferencesText:
            ##################### second call to the API: send references and get back the matched references
            # /reference/{timestamp}/{citing}/{style}/{reference}
            request = requests.get('http://localhost:8000/api/reference/'+str(web.input().time)+'/'+web.input().idRef+'/'+web.input().style+'/'+urllib.parse.quote(referenceText) )
            response = request.json()
            referenceMatch = {}
            referenceMatch['submitted'] = referenceText
            referenceMatch['match'] = response[0]['reference']
            referenceMatch['id'] = response[0]['id']
            results.append(referenceMatch)
            ##################### remove the following lines
            # encodedReference = '+'.join(word for word in re.compile('\w+').findall(referenceText))
            # request = requests.get('http://api.crossref.org/works?query='+encodedReference+'?sample=1&select=DOI,title')
            # referenceMatch = {}
            # referenceMatch['submitted'] = referenceText
            # referenceMatch['match'] = request.text
            # referenceMatch['id'] = '123'
            # results.append(referenceMatch)
        #sortedResults = sorted(results.items(), key=lambda x: x[0])
        print(results)
        return render.results(results=results, content='Placeholder for the citing entity')

if __name__ == "__main__":
	app = web.application(urls, globals())
	app.internalerror = web.debugerror
	app.run()