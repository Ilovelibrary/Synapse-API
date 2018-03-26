#!/usr/bin/python
# -*- coding: utf-8 -*-
from flask import Flask, request, render_template
import requests
import datetime

# API initialization and set header
client_id = ''   # your client id
client_secret = ''   # your client secret
fingerprint = ''
ip_address = ''   # user's IP

headers = {
    'X-SP-GATEWAY': client_id + '|' + client_secret,
    'X-SP-USER-IP': ip_address,
    'X-SP-USER': '|' + fingerprint
}

baseURL = 'https://uat-api.synapsefi.com/v3.1'

# Build the server and set the routes
app = Flask(__name__, static_url_path="", static_folder="static")

# homepage route
@app.route('/')
def index():
    return render_template('index.html')

# route for users list
@app.route('/users')
def users():
    URL = baseURL+'/users'
    resp = requests.get(URL, headers=headers).json()
    users = resp['users']
    
    return render_template('users.html', users=users)

# route for all nodes of a user
@app.route('/users/<user_id>')
def nodes(user_id):
    # get information of the user and authenticate
    URL = baseURL + '/users/' + user_id
    resp = requests.get(URL, headers=headers).json()
    refreshToken = resp['refresh_token']
    oauthURL = baseURL + '/oauth/' + user_id
    oauthResp = requests.post(oauthURL, headers=headers, json={'refresh_token': refreshToken}).json()
    oauthKey = oauthResp['oauth_key']
    # reset the header with oauth key
    headers['X-SP-USER'] = oauthKey + '|' + fingerprint
    # fetch node info with new header
    URL = baseURL + '/users/' + user_id+'/nodes'
    resp = requests.get(URL, headers=headers).json()
    nodes = resp['nodes']
    
    return render_template('nodes.html', nodes=nodes, user_id=user_id)

# route for all transactions of a node
@app.route('/users/<user_id>/nodes/<node_id>/trans')
def trans(user_id, node_id):
    # get transactions with the same header
    URL = baseURL + '/users/' + user_id + '/nodes/' + node_id + '/trans'
    resp = requests.get(URL, headers=headers).json()
    trans = resp['trans']
    
    return render_template('trans.html', trans=trans)

# route for statistics of transactions
@app.route('/stats')
def stats():
    URL = baseURL + '/users'
    resp = requests.get(URL, headers=headers).json()
    users = resp['users']
    trans = []
    # traverse all users to get all transactions
    for user in users:
        # authenticate first before get transactions
        URL = baseURL + '/users/' + user['_id']
        resp = requests.get(URL, headers=headers).json()
        refreshToken = resp['refresh_token']
        oauthURL = baseURL + '/oauth/' + user['_id']
        oauthResp = requests.post(oauthURL, headers=headers, json={'refresh_token': refreshToken}).json()
        oauthKey = oauthResp['oauth_key']
        headers['X-SP-USER'] = oauthKey + '|' + fingerprint
        URL = baseURL+'/users/' + user['_id'] + '/trans'
        resp = requests.get(URL, headers=headers).json()
        trans += resp['trans']
        
    # define a function to get location by ip address of transaction
    def get_location(adress):
        api = "http://freegeoip.net/json/" + adress
        resp = requests.get(api).json()
        return [resp['latitude'], resp['longitude']]
    
    points = [['Lat', 'Long']]   # store the locations shown on the map  
    dates = {}   # store the numebr of transaction in each of the previous 15 days
    today = datetime.datetime.now()
    for i in range(15):
        dates[today.strftime('%Y-%m-%d')] = 0
        today = today-datetime.timedelta(days=1)
    
    # traverse transactions to fill the data of the map and chart
    for tran in trans:
        # filter some transactions with wrong ip addresses
        if get_location(tran['extra']['ip']) != [0, 0]:
            points.append(get_location(tran['extra']['ip']))
            date = datetime.datetime.fromtimestamp(tran['extra']['created_on']/1000).strftime('%Y-%m-%d')
            if date in dates:
                dates[date] += 1
    keys = sorted(dates)
    chartData = [keys, [dates[k] for k in keys]]
    
    return render_template('stats.html', points=points, chartData=chartData)

if __name__ == '__main__':
    app.secret_key = 'super-secret-key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
