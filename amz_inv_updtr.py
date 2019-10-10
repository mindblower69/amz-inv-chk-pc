#Version 0.6.5

#Good version
#Still needs to be done:
#Hosting
#Schedule
#Make sure we don't affect the same sku twice
#Set up failsafes for errors
#Write failed api calls and error logs to a file (daily_error_log)
#Write a report for SKUs that can't be outright taken out (duplicates issues)


#requests: For API Calls
#datetime: to access current time
#time: certain method relating to time format
#urllib: converts some elements to respect the url that the API demands
#base64, hashlib, hmac: All for encryption and the Signature of the Canonical Query String
#re:
#imaplib:
#getpass: Like input() but hides the input data when typing
#email: Library for parsing email data from imap
#sys: makes it so we can use "child_process" from node
#utils: Can be found locally thanks to from __future__ import absolute_import
#from __future__ import absolute_import
#importing dependencies:
import requests
#importing built-in modules:
import datetime, time, urllib, base64, hashlib, hmac, re, imaplib, getpass, email, sys, os
#local version, also not in use at the moment
#import utils
MWS_API=[{"Action":"RequestReport", "Version":"2009-01-01", "Reqd_ParamNameA":"ReportType", "ReportType":"_GET_FLAT_FILE_OPEN_LISTINGS_DATA_", "HTTP_Method":"POST", "HTTP_Path":"/"},
         {"Action":"GetReportList", "Version":"2009-01-01", "Reqd_ParamNameA":"ReportRequestIdList.Id.1", "HTTP_Method":"POST", "HTTP_Path":"/"},
         {"Action":"GetReport", "Version":"2009-01-01", "Reqd_ParamNameA":"ReportId", "HTTP_Method":"POST", "HTTP_Path":"/"},
         {"Action":"SubmitFeed", "Version":"2009-01-01", "Reqd_ParamNameA":"FeedType", "Reqd_ParamNameB":"ContentMD5Value","Reqd_ParamNameC":"PurgeAndReplace", "HTTP_Method":"POST", "HTTP_Path":"/"}]

dict_res={}
sku_list_rem=[]
#sku_list_remd=[]
#os.environ.get('APP_PASSWORD')
app_pass = "dwhmkkqswkutirjr"
#os.environ.get('APP_ADDRESS')
app_mail = "automatpc.41@gmail.com"


#Starting to define functions, seperate features in prep for logic loop
#Generates HTTP Header
def generateHTTPHeader(diction):
    MWS_API=diction
    #Creates the HTTP Header for the req
    HTTP_Header=MWS_API["HTTP_Method"]+"\n"+MWS_API["HTTP_Host"]+"\n"+MWS_API["HTTP_Path"]+"\n"
    return HTTP_Header


#Generates a Canonical Query String or URI
def generateRequest(diction, query_content_list):
    canon_query_list=[]
    MWS_API=diction
    #Assembling the Canonical Query String
    for keyword, value in sorted(MWS_API.items()):
        if keyword in query_content_list:
            canon_query_list.append('%s=%s' % (keyword, urllib.parse.quote(value)))
        #if "Reqd_ParamName" in keyword:
        #canon_query_list.append('%s=%s' % (value, urllib.parse.quote(MWS_API[value])))
    req= "&".join(canon_query_list)
    return req


#Generates the signature for the Canonical Query String
def signatureCanonQuery(diction, string):
    MWS_API = diction
    HTTP_Header= generateHTTPHeader(MWS_API)
    req=string
    canon_query_string=HTTP_Header+req
    utfEncoded_canon_query_string = canon_query_string.encode('utf-8')
    h_digested = hmac.new(MWS_API['SecretKey'], utfEncoded_canon_query_string, digestmod=hashlib.sha256).digest()
    API_Signature=base64.b64encode(h_digested)
    API_Signature_string = str(API_Signature)
    return API_Signature_string

#Generate XML templates
def assignXMLTemplates():
    XML_Templates={}
    XML_Templates.update({"start":"""<?xml version="1.0" encoding="utf-8"?>
    <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
    <Header>
    <DocumentVersion>1.01</DocumentVersion>
    <MerchantIdentifier>A165OVU2YPVBWX</MerchantIdentifier>
    </Header>
    <MessageType>Inventory</MessageType>
    """})
    XML_Templates.update({"message":"""<Message>
    <MessageID>{messageID}</MessageID>
    <OperationType>Update</OperationType>
    <Inventory>
    <SKU>{sku}</SKU>
    <Quantity>{itemQuant}</Quantity>
    </Inventory>
    </Message>
    """})
    XML_Templates.update({"end":"""</AmazonEnvelope>"""})
    return XML_Templates

#Calculates the MD5 from the XML Content as string form
def calc_md5(string):
    """
    Calculates the MD5 encryption for the given string
    """
    md5_hash = hashlib.md5()
    if type(string) != bytes:
        stringA=string.encode()
        md5_hash.update(stringA)
    else:
        md5_hash.update(string)
    return base64.b64encode(md5_hash.digest()).strip(b'\n')

def fetch_mail(a_email, a_pass):
    #Takes care of logging in
    #import imaplib, getpass, email
    email_address = a_email
    password = a_pass
    print(email_address)
    print(os.environ.get('APP_ADDRESS'))
    #getpass.getpass('Password:')
    M = imaplib.IMAP4_SSL('imap.gmail.com')
    M.login(email_address, password)

    #Interacts with messages and folders
    #-M.list()
    M.select('inbox')
    #-Search features
    #--Do only 1 time
    #typ, data = M.search(None, 'SUBJECT "retirer sur le site"')
    #--Do this search from now on, (add date from yesterday till now)
    yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
    time_day = yesterday.strftime('%d')
    time_month = yesterday.strftime('%h')
    time_year = yesterday.strftime('%Y')

    search_query = '(SUBJECT "retirer sur le site" SINCE "{day}-{month}-{year}")'.format(day=time_day,month=time_month,year=time_year)

    typ, data = M.search(None, search_query)
    #--These are the email IDs matching our search
    email_id = data[0]
    email_id_string = email_id.decode('utf-8')
    email_id_list = email_id_string.split(' ')
    #Fetches the actual email data, parses it and trims the stuff we dont need leaving us with a list of SKUs
    sku_list_em = []
    goal = len(email_id_list)
    #- range(len(email_id_list))
    for item in range(len(email_id_list)):
        #This ensures we don't run into issues with request quotas, this should be tested.
        if(item%25==0 and item!=0):
            time.sleep(1)
        result, email_data = M.fetch(email_id_list[item], '(RFC822)')
        raw_email_string =email_data[0][1].decode('utf-8', 'backslashreplace')
        email_message = email.message_from_string(raw_email_string)
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True)
                body_string = body.decode('utf-8')
                skuAll = re.findall(r'\d{5,6}-\d{1,3}\w{0,5}|\d{8,14}\w{0,5}',body_string)
                for sku in skuAll:
                    sku_list_em.append(sku)

        print("Progress: {itA}/{goB}".format(itA = (int(item)+1), goB = goal))
    print(sku_list_em)

    #Takes care of logging out and closing current mail
    M.close()
    M.logout()
    return sku_list_em


#XML Parsing

def remove_namespace(xml):
    """
    Strips the namespace from XML document contained in a string.
    Returns the stripped string.
    """
    regex = re.compile(' xmlns(:ns2)?="[^"]+"|(ns2:)|(xml:)')
    return regex.sub('', xml)

def dict_response(xml):
    if "sku	asin	price	quantity" not in xml:
        #Parses the xml returns a string without return carriage, newlines or whitespaces
        xml_string = remove_namespace(xml).replace('\n', '').replace('\r', '').replace(" ","")
        #Fetch every useful nodes and their content
        print(xml_string)
        print('\n')
        xml_search_key = re.findall(r'</\w*>', xml_string)
        #print(xml_search_key)
        #print(len(xml_search_key))
        #You'll likely need to add characters as we expand on the type of calls we make
        xml_search_content = re.findall(r'>[A-Za-z0-9\:\.\+_-]*</', xml_string)
        #print(xml_search_content)
        #print(len(xml_search_content))
        res_dict = {}
        #Makes sure that we indeed have the same amount of keys and content, also take out empty nodes
        content_list=[]
        if len(xml_search_content) == len(xml_search_key):
            for itr in range(len(xml_search_key)):
                key=xml_search_key[itr][2:-1]
                content=xml_search_content[itr][1:-2]
                if key != "" and content != "":
                    if key in xml_search_key and content not in xml_search_content and key in res_dict:
                        if type(res_dict[key]) == list:
                            content_list=res_dict[key]
                        else:
                            content_list.append(res_dict[key])
                        content_list.append(content)
                        res_dict[key] = content_list
                    else:
                        pair = {key:content}
                        res_dict.update(pair)
            return res_dict
        else:
            errMessage = "Unexpected case: The number of content does not match the number of key"
            return errMessage
    else:
        print('sku-list')
        amz_sku_list=[]
        amz_quant_list=[]
        amz_item_list = xml.split()
        print(amz_item_list)
        print(len(amz_item_list))
        sku_len=32
        quant_len=32
        amz_item_dict_list={}
        j=0
        k=0
        for i in range(len(amz_item_list)):

            if(i%4==0):
                amz_sku_list.append(amz_item_list[i])
                print(amz_item_list[i])
                sku_len = len(amz_item_list[i])
                print(amz_item_list[i+3])
                quant_len = len(amz_item_list[i+3])
                if quant_len > 3 and amz_item_list[i+3]!="quantity":
                    errMessage='Anomaly found: Quantity length is unusual, possibly missing - {} - Fix provided: 0 inserted to replace missing value'.format(amz_item_list[i+3])
                    print(errMessage)
                    amz_item_list.insert(i+3, '0')
                if sku_len <= 3 and amz_item_list[i]!="sku":
                    errMessage = 'Anomaly found: SKU length is unusual, possibly missing - {}'.format(amz_item_list[i])
                    return errMessage
                amz_quant_list.append(amz_item_list[i+3])
        if len(amz_sku_list) == len(amz_quant_list):
            amz_item_dict_list.update({amz_sku_list[0]:amz_sku_list[1:]})
            amz_item_dict_list.update({amz_quant_list[0]:amz_quant_list[1:]})
            return amz_item_dict_list
        else:
            errMessage = "Unexpected case: The number of SKU does not match the number of Quantity"
            return errMessage


def mwsRequest(diction, dict_res={}, sku_list=[]):
    User_constants = {"HTTP_Host":"mws.amazonservices.ca", "Merchant":"A165OVU2YPVBWX", "MarketplaceIdList":"A2EUQ1WTGCTBG2", "AWSAccessKeyId":"AKIAJF2LKQNWFWBULCXA", "SignatureVersion":"2", "SignatureMethod":"HmacSHA256"}
    User_constants_private = {"MWSAuthToken":"amzn.mws.3eb15811-66ee-4ede-ee6e-04ccf990112d", "SecretKey":b"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"}
    #This will somewhat simplify the process of creating the query string, in terms of readibility
    canon_query_list_content=["Action","Merchant","AWSAccessKeyId","SignatureVersion","SignatureMethod","MWSAuthToken","Timestamp","Version"]
    canon_query_list=[]
    #sku_list_rem=[{"sku":"168353-25val", "currentQuant":1}]
    #sku_list=sku_list_rem
    #MWS_API is a list of dictionaries, one for each API call that we require, it contains API Action specific changes
    XML_Templates= assignXMLTemplates()
    MWS_API={}
    MWS_API=diction
    paramA=dict_res
    print(MWS_API['Action'])
    if MWS_API['Action'] == "GetReportList":
        MWS_API.update({MWS_API["Reqd_ParamNameA"]: paramA['ReportRequestId']})
        print("This is ParamA under Get Report List")
        print(paramA)
    if MWS_API['Action'] == "GetReport":
        MWS_API.update({MWS_API["Reqd_ParamNameA"]: paramA['ReportId']})
        print("This is ParamA under Get Report")
        print(paramA)
    canon_query_list_content.append(MWS_API["Reqd_ParamNameA"])
    #Timestamp and Signature need to be generated at run time
    #Timestamp
    API_Timestamp = ( datetime.datetime.utcfromtimestamp( time.time() ) ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    #Assemble all elements into MWS_API
    MWS_API.update({"Timestamp":API_Timestamp})
    MWS_API.update(User_constants)
    MWS_API.update(User_constants_private)

    if MWS_API['Action'] == "SubmitFeed":
        paramA="_POST_INVENTORY_AVAILABILITY_DATA_"
        MWS_API.update({MWS_API["Reqd_ParamNameA"]: paramA})
        canon_query_list_content.append(MWS_API["Reqd_ParamNameA"])
        paramC="false"
        MWS_API.update({MWS_API["Reqd_ParamNameC"]: paramC})
        canon_query_list_content.append(MWS_API["Reqd_ParamNameC"])
        #Dont think we need to specify a PurgeAndReplace parameter since we can do it from the body of the XML
        #XML
        #XML Header
        XML_Header = {'Content-Type': 'text/xml'}
        #XML Content
        XML_Content = XML_Templates["start"].format(merchID=MWS_API['Merchant'])
        for k in range(len(sku_list)):
            XML_Content += XML_Templates["message"].format(messageID=str(int(k)+1),sku=sku_list[k]['sku'],itemQuant=str(int(sku_list[k]['currentQuant'])-1))
        XML_Content += XML_Templates["end"]
        #f = open("xml_test.xml", "r")#XML_Content = f.read()#f.close()#MWS_Body={"FeedContent": XML_Content}
        print(XML_Content)
        print('\n')

        XML_md=calc_md5(XML_Content)
        #Maybe you don't base64 it if you're gonna sign it?
        #paramB=XML_md

        #MWS_API.update({MWS_API["Reqd_ParamNameB"]: paramB})
        #canon_query_list_content.append(MWS_API["Reqd_ParamNameB"])

    #Generates Canonical String and then it's Signature
    req=generateRequest(MWS_API, canon_query_list_content)
    API_Signature_string = signatureCanonQuery(MWS_API, req)

    req+='&Signature=%s' % urllib.parse.quote(API_Signature_string[2:-1])
    baseurl="https://mws.amazonservices.ca/?"
    print(req)
    #User-Agent header, no Host=value yet
    #useragent="x-amazon-user-agent:PayonsComptant/build006(Language=Python)"  'User-Agent':'PayonsComptant/build006(Language=Python)'
    apicall= baseurl+req
    print(apicall)
    if MWS_API['Action'] == "SubmitFeed":
        #res = requests.post(apicall, data=XML_Content, headers={'User-Agent': 'python-amazon-mws/0.8.6 (Language=Python)','Content-MD5':XML_md, 'Content-type':'text/xml'})
        res = requests.post(apicall, data=XML_Content, headers={'User-Agent': 'python-amazon-mws/0.8.6 (Language=Python)','Content-MD5':XML_md, 'Content-type':'text/xml'})
    else:
        res = requests.post(apicall)
    #Needs to be replaced with subcription to report status
    countTimer=0
    if MWS_API['Action'] == "GetReportList":
        dict_resB=dict_response(res.text)
        while 'ReportId' not in dict_resB and countTimer < 60:
            res = requests.post(apicall)
            dict_resB=dict_response(res.text)
            time.sleep(5)
            countTimer+=5
        if 'ReportId' not in dict_resB:
            errMessage={"errorMessage":"Manually Timed out after 60 seconds"}
            return errMessage




    if 'ErrorResponse' in res.text:
        result = re.search('<Message>(.*)</Message>', res.text)
        print(result)
        return res.text
        #print('\n')
        #print(res)
        #print(result.group(0))
    else:
        #print("\n")
        #print(res.status_code)
        #print("\n")
        #print(res.headers)
        #print("\n")
        #print(res.text)
        return res.text





#Logic Loop
for item in MWS_API:
    if item['Action']=='SubmitFeed':
        em_sku_list = fetch_mail(app_mail, app_pass)
        amz_sku_list_dict = dict_res
        print("amz_sku_list_dict :")
        print(amz_sku_list_dict)

        for store_item in range(len(amz_sku_list_dict['sku'])):
            for em_sku in em_sku_list:
                if em_sku in amz_sku_list_dict['sku'][store_item] and int(amz_sku_list_dict['quantity'][store_item]) > 0:
                    sku_list_rem.append({"sku":amz_sku_list_dict['sku'][store_item], "currentQuant":int(amz_sku_list_dict['quantity'][store_item])})
                    print("sku_list_rem :")
                    print(sku_list_rem)
    xml_res = mwsRequest(item, dict_res, sku_list_rem)
    #This is a save of the already removed items, so not to have repeats through out the day
    #sku_list_remd = sku_list_rem
    print("This is XML response before parsing")
    print(xml_res)
    dict_res = dict_response(xml_res)
    print('dict_res :')
    print(dict_res)

print('done')
