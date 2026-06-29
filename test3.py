import urllib.request
try:
    req = urllib.request.Request('https://www.signalhire.com/api/v1/candidate/enrich', headers={'ApiKey': '202.XzikXnDLu6RVvOnmsCKfZI7TuDap', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    with urllib.request.urlopen(req) as response:
        print(response.read())
except Exception as e:
    print(repr(e))
