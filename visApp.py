import requests
import sys
import os
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, json, jsonify


app = Flask(__name__)


apikey = ''
collection_id = ''
environment_id = ''
endpoint = 'https://gateway.watsonplatform.net/discovery/api'


@app.route('/')
def error():
    return "Please specify a search term in your URL"


@app.route('/viewvHeadline', methods=['POST'])
def viewvHeadline():
    id = request.json['id']
    version = '2018-12-03'

    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query&query=id:'+id+'&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('version', apikey)) 
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev

    except Exception as e:
        print("Exception = ",e)
     
    output = { 'response': response }  
    return jsonify(output)
 

@app.route('/newHeadlines', methods=['POST'])
def newHeadlines():
    combo = request.json['combo']
    comboWords=combo.replace("\"","").split('|')

    combos=[]
    headlines={}
    version = '2018-12-03'
    
    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query?deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text::'+combo+'&return=text&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('apikey', apikey)) 
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev

        for article in response['results']:
            text_full=article['text']
            text_clip=text_full[:80]
            combos[:]=[]
            for word in comboWords:
                if word.upper() in article['text'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][text_clip]=article['id']
            
    except Exception as e:
        print("Exception = ",e)

    output = { 'headlines': headlines }  
    return jsonify(output)


@app.route('/click', methods=['GET', 'POST'])
def click():
   
    nodes=request.json['nodes']
    links=request.json['links']
    bigWords=request.json['bigWords']
    index=request.json['current']
    
    x = nodes[index]['x']
    y = nodes[index]['y']
    text = nodes[index]['text']
    version = '2018-12-03'

    length = len(nodes)
    words={}
    headlines={}
    combo=""
    comboWords=[]
    combos=[]
    for node in nodes:
        words[node['text']] = node['index']
        if node['expand'] == 1:
            comboWords.append(node['text'])
    for word in comboWords:
        combo+="\""+word+"\"|"
    combo=combo[:-1]

    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query?deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text::'+combo+'&return=text&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('apikey', apikey)) 
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev
        
        for article in response['results']:
            text_full=article['text']
            text_clip=text_full[:80]
            combos[:]=[]
            for word in comboWords:
                if word.upper() in article['text'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][text_clip]=article['id']

    except Exception as e:
        print("Exception = ",e)
    
    output = { 'results': { 'nodes': [], 'links': [], 'headlines': headlines, 'combo': combo } }
 
    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query?aggregation=nested(enriched_text.entities).filter(enriched_text.entities.type::"Person").term(enriched_text.entities.text,count:10)&deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text::"'+text+'"&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('apikey', apikey)) 
        response=results.json()
        # print(json.dumps(response, indent=2)) # dev
        
        #add to bigWords
        wordList = []
        for kword in response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
            wordList.append(kword['key'])
        bigWords[text]={'wordList':wordList,'expand':1}  
        output['results']['bigWords']=bigWords    
        count1=0 
        count2=0

        for newWord in bigWords[text]['wordList']:
            if newWord in words:
                    output['results']['links'].append({'source':index,'target':words[newWord]})
                    continue
            if count2 < 5:    
                for bigWord in bigWords:
                    if bigWords[bigWord]['expand']==0:
                        continue
                    if bigWord == text:
                        continue
                    if newWord in bigWords[bigWord]['wordList']:
                        if newWord not in words:
                            output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})
                            words[newWord]=length
                            length+=1
                            count2+=1
                        output['results']['links'].append({'source':words[newWord],'target':words[bigWord]})
                        output['results']['links'].append({'source':words[newWord],'target':index})
            if newWord not in words and count1 < 5:
                output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})   
                output['results']['links'].append({'source':length,'target':index})
                length+=1
                count1+=1
                    
    except Exception as e:
        print("Exception = ",e)
                
    return jsonify(output)


@app.route('/favicon.ico')
def favicon():
   return ""



# @app.route('/keyword', methods=['GET'])
# def news_page():
    # keyword = request.args.get('keyword')
@app.route('/<keyword>')
def news_page(keyword):

    index=0
    nodes=[]
    links=[]
    headlines={}
    headlines[1]={}
    headlines[1][keyword]={}
    bigWords={}
    version='2018-12-03'

    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query?deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text::"'+keyword+'"&return=text&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('apikey', apikey)) 
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev
        
        for article in response['results']:
            text_full=article['text']
            text_clip=text_full[:80]
            headlines[1][keyword][text_clip]=article['id']
            
    except Exception as e:
        print("Exception = ",e)
 
    try:
        get_url = endpoint+'/v1/environments/'+environment_id+'/collections/'+collection_id+'/query?aggregation=nested(enriched_text.entities).filter(enriched_text.entities.type::"Person").term(enriched_text.entities.text,count:10)&deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text::"'+keyword+'"&version='+version
        # results = requests.get(url=get_url, auth=(username, password)) 
        results = requests.get(url=get_url, auth=('apikey', apikey)) 
        response=results.json()
        # print(json.dumps(response, indent=2)) # dev

        #add to bigWords
        wordList = []
        for kword in response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
            wordList.append(kword['key'])
        bigWords[keyword]={'wordList':wordList,'expand':1}   
    except Exception as e:
        print("Exception = ",e)
 
    count=0
    nodes.insert(0, {'x': 300, 'y': 200, 'text': keyword, 'size': 3, 'fixed': 1, 'color': '#0066FF', 'expand': 1})
    for word in bigWords[keyword]['wordList']:
        if count > 9:
            break
        if word == keyword:
            continue
        else:
            nodes.append({'x': 300, 'y': 200, 'text': word, 'size': 1.5, 'color': 'white', 'expand': 0})
            links.append({'source':count + 1,'target':0})
            count+=1
         
    return render_template('cloud.html', nodes=json.dumps(nodes), links=json.dumps(links), bigWords=json.dumps(bigWords), headlines=json.dumps(headlines))

port = os.getenv('VCAP_APP_PORT', '8000')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(port), debug=True)
