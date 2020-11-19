import socket
from html.parser import HTMLParser

target_host = "www.3700.network"
target_port = 80
urls_to_be_scraped = []
urls_visited = {}
cookies = {}
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((target_host, target_port))

# Create a new socket


def new_socket():
    global client
    client.close()
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket.connect((target_host, target_port))
    client = new_socket

# Receive response from socket


def recv(cli):
    result = bytearray()
    while True:
        response = cli.recv(4096)
        result.extend(response)
        if r'0\r\n\r\n' in str(result) or r'Transfer-Encoding: chunked' not in str(result):
            break
    if r'Connection: keep-alive' not in str(result):
        new_socket()
    return result.decode('utf-8')

# handle http based on status code


def handle_http(http, url):
    global cookie, urls_visited
    seperated = read_http(http)
    status, headers, body = seperated['status'], seperated['headers'], seperated['body']

    # update cookie if needed
    for header in headers:
        key, value = header.split(": ", 1)
        if key == 'Set-Cookie':
            type = value.split("; ")[0].split('=')[0]
            cookies[type] = value.split("; ")[0]
    cookie = '; '.join(cookies.values())

    # 200
    if status == "200":
        return body

    # 302
    elif status == "302":
        for header in headers:
            key, value = header.split(": ", 1)
            if key == "Location":
                if value in urls_visited:
                    print('Redirect to a site visited')
                    return False
                http = get_request(value)
                return handle_http(http, value)
    # 403/404
    elif status == "403" or status == "404":
        print("[ABANDON]: 403/404 Found")
        return False

    # 500
    elif status == '500':
        http = get_request(url)
        return handle_http(http, url)

# Send get request to url


def get_request(url):
    global cookie, client

    headers = "Host:{}\r\nCookie:{}".format(
        target_host, cookie)
    request = "GET {} HTTP/1.1\r\n{}\r\n\r\n".format(url, headers)
    client.send(request.encode())
    response = recv(client)

    while response == "":
        new_socket()
        client.send(request.encode())
        response = recv(client)

    return response

# Seperate one http response into status, header and body


def read_http(http):
    http = http.split('\r\n\r\n')
    headers = http[0].split('\r\n')[1:]
    status = http[0].split('\r\n')[0].split(' ')[1]
    body = http[1]
    return {'status': status, 'headers': headers, 'body': body}


def scrape(http, url):
    global urls_to_be_scraped, urls_visited
    parse_html(http, url)

    while len(urls_to_be_scraped) > 0:
        next_url = urls_to_be_scraped[0]
        next_http = get_request(next_url)
        urls_to_be_scraped = urls_to_be_scraped[1:]
        parse_html(next_http, next_url)
    return


def parse_html(http, url):
    global urls_to_be_scraped, urls_visited
    body = handle_http(http, url)
    if body:
        parser.feed(body)

    return

# HTML parser


class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.recording = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    url = attr[1]
                    # only add url from the same host
                    if attr[1][0] == '/':
                        url = "http://" + target_host + url
                        if url not in urls_visited:
                            urls_to_be_scraped.append(url)
                            urls_visited[url] = True
        elif tag == 'h2':
            for attr in attrs:
                if 'secret_flag' in attr:
                    self.recording = True

    def handle_endtag(self, tag):
        if tag == 'h2' and self.recording:
            self.recording = False

    def handle_data(self, data):
        if self.recording:
            print(data)
        return


parser = MyHTMLParser()

# login page
request = "GET http://www.3700.network/accounts/login/?next=/fakebook/ HTTP/1.1\r\nHost:%s\r\n\r\n" % target_host
client.send(request.encode())
response = recv(client)

urls_visited['http://www.3700.network/accounts/login/?next=/fakebook/'] = True
seperated = read_http(response)
status, headers = seperated['status'], seperated['headers']

# Cookie initiation
for header in headers:
    key, value = header.split(": ", 1)
    if key == 'Set-Cookie':
        type = value.split("; ")[0].split('=')[0]
        cookies[type] = value.split("; ")[0]
cookie = '; '.join(cookies.values())

request_body = 'username=1862143&password=1KG4UQ1N&csrfmiddlewaretoken={}&next=/fakebook/'.format(
    cookies['csrftoken'].split('=')[1])
request_header = "Host:{}\r\nCookie:{}\r\nAccept-Encoding:gzip\r\nConnection:Keep-Alive\r\nContent-Length:{}\r\nContent-Type:application/x-www-form-urlencoded".format(
    target_host, cookie, str(len(request_body.encode())))

# login request
request = "POST http://www.3700.network/accounts/login/ HTTP/1.1\r\n{}\r\n\r\n{}".format(
    request_header, request_body)

client.send(request.encode())

home_page = recv(client)

# start scraping
scrape(home_page, 'http://www.3700.network/fakebook/')
client.close()
