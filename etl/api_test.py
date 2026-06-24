import requests

titulo = "Wednesday"

url = f"https://api.tvmaze.com/search/shows?q={titulo}"

response = requests.get(url)

data = response.json()

print(data[0]["show"]["name"])
print(data[0]["show"]["language"])
print(data[0]["show"]["status"])
print(data[0]["show"]["rating"]["average"])