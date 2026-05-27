# Anuraga Profile
request:
```
curl 'https://www.anuragamatrimony.com/profile.php?id=AGM000000' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -b 'ANURAGASESSID=b49465fd2b168779cfb6c012dc59bc34' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://www.anuragamatrimony.com/searchresult.php?id=AGM000000&mode=direct' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Sec-Fetch-User: ?1' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0' \
  -H 'dnt: 1' \
  -H 'sec-ch-ua: "Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-gpc: 1'
```

response is a HUGE HTML, in that HTML response, here are the fields we want:
- Age: `document.querySelector("#tab_0 > div:nth-child(2) > span:nth-child(2)")`
- Height: `document.querySelector("#tab_0 > div:nth-child(3) > span:nth-child(2)")`
- Date of birth: `document.querySelector("#tab_1 > div.group_el_5.field_socialsettings.member_profilefield > span:nth-child(2)")`
- Time of birth: `document.querySelector("#tab_1 > div:nth-child(6) > span:nth-child(2)")`
- Nakshatra: `document.querySelector("#tab_1 > div:nth-child(8) > span:nth-child(2)")`
- Gotra: `document.querySelector("#tab_1 > div:nth-child(7) > span:nth-child(2)")`
- Rashi: `document.querySelector("#tab_1 > div:nth-child(9) > span:nth-child(2)")`


# Anuraga images
You nede to do a `GET https://www.anuragamatrimony.com/photos.php?id={AGM_ID_HERE}&&pp=1`
You'll get a HTML page with upto 3 images. Below are the `img` tag itself, you can call the `src=` URL (it might be relative!) to get the image
Image 1: `document.querySelector("body > div > table > tbody > tr > td:nth-child(1) > a:nth-child(1) > img")`
Image 2: `document.querySelector("body > div > table > tbody > tr > td:nth-child(1) > a:nth-child(4) > img")`
Image 3: `document.querySelector("body > div > table > tbody > tr > td:nth-child(1) > a:nth-child(7) > img")`



# Aseema Profile
request:
```
curl 'https://aseemamatrimony.in/profile/view/39657' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -b 'ci_session=c33de25dcb5e6116f6758452a9bfd032e5efe8c7' \
  -H 'Pragma: no-cache' \
  -H 'Referer: https://aseemamatrimony.in/account/dashboard.html' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Sec-Fetch-User: ?1' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0' \
  -H 'dnt: 1' \
  -H 'sec-ch-ua: "Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-gpc: 1'
```

response is a HUGE HTML, in that HTML response, here are the fields we want:

- Name: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-7.row_1 > table > tbody > tr:nth-child(1) > td.day_value")`
- Age: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-7.row_1 > table > tbody > tr.opened_1 > td.day_value")`
- Height: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-7.row_1 > table > tbody > tr:nth-child(5) > td.day_value")`
- Date of birth: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-7.row_1 > table > tbody > tr:nth-child(4) > td.day_value")`
- Nakshatra: `document.querySelector("#home > form:nth-child(2) > div > div:nth-child(2) > table > tbody > tr:nth-child(1) > td.day_value.closed > span")`
- Gotra: `document.querySelector("#home > form:nth-child(2) > div > div:nth-child(2) > table > tbody > tr:nth-child(2) > td.day_value.closed > span")`
- Rashi: `document.querySelector("#home > form:nth-child(2) > div > div:nth-child(2) > table > tbody > tr:nth-child(3) > td.day_value.closed > span")`


# Aseema images

You'll find upto 4 images PER profile, below are the JS paths directly to the `img` tag itself (that has the `src=` from where you can download the image)
Image 1: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-5.row_2 > div > div > ul > li:nth-child(1) > img")`
Image 2: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-5.row_2 > div > div > ul > li:nth-child(2) > img")`
Image 3: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-5.row_2 > div > div > ul > li:nth-child(3) > img")`
Image 4: `document.querySelector("#page > section > div > div > div > div > article > div > div > div > div.col_3 > div.col-sm-5.row_2 > div > div > ul > li:nth-child(4) > img")`
