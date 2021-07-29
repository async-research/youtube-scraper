from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd 
import time, json, datetime


class YouTubeScraper:
    def __init__(self, driver_path, headless=True,  wait=60):
        """
        Get videos/data from YouTube.  

        Parameters:
            driver_path: a str type, containing the path for your Chrome driver.
            headless: a boolean type, toggle headless mode. 
            wait: a int type, set wait time. 

        """
        self._chrome_options = Options()
        if headless:
            self._chrome_options.add_argument("--headless")
        else:
            self._driver.maximize_window()
        self._driver = webdriver.Chrome(options=self._chrome_options, executable_path=driver_path)
        self._wait = WebDriverWait(self._driver, wait)

    def search(self, search_query='rickroll', meta_data=False, save=False, scale=0):
        """
        Search for videos on YouTube 

        Paramerters
            search_query: a str type containing search query for YouTube. 
            meta_data: a boolean type,  True : return  a list of dcts with metadata.
                                        False: return a list of videoIDs
                                       
            save: a boolean type,  True: save DataFrame to local dir as a .csv file. 
            scale: a int type, Determines the scale of how many videos are visible to 
                  Chrome by scrolling by this amount.
        Returns:
            A list of videoIDs  or panda DataFrame containing metadata of each videoID

        """
        url = "https://www.youtube.com/results?search_query="+search_query
        self._driver.get(url)
        for i in range(scale): 
            time.sleep(1)
            self._wait.until(EC.visibility_of_element_located((By.TAG_NAME, "body"))).send_keys(Keys.PAGE_DOWN)

        videos = []
        for video in self._wait.until(EC.presence_of_all_elements_located((By.ID, 'video-title'))):
            video_id = video.get_attribute("href")
            if video_id:
                video_id = video_id.replace("https://www.youtube.com/watch?v=","")
                videos.append(video_id)

        if meta_data:
            results = []
            for video_id in videos:
                try:
                    data = self.get_video_meta_data(video_id)
                except Exception as e:
                    print("Error Detected! ", e)
                else:
                    print(data)
                    results.append(data)
                    time.sleep(1)
            videos_dataframe = pd.DataFrame(results, columns=['videoID','likes','dislikes','viewCount','uploadDate','category']) 

            if save:
                videos_dataframe.to_csv(f"youtube_webscrape_{search_query.replace(' ','-')}.csv")

            return videos_dataframe

        else:
            return videos

    def get_video_meta_data(self, videoID):
        """
        Web scrape meta data of a video.

        Parameters:
            videoID: a str type, contains a videoID

        Returns:
            data: a dictionary type, containing video metadata.

        """
        url = "https://www.youtube.com/watch?v="+videoID
        self._driver.get(url)
        data = {}
        likes_element = self._wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-menu-renderer.ytd-video-primary-info-renderer > div:nth-child(1) > ytd-toggle-button-renderer:nth-child(1) > a:nth-child(1) > yt-formatted-string:nth-child(2)")))
        likes_attribute = likes_element.get_attribute('aria-label')
        dislikes_element = self._wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-menu-renderer.ytd-watch-metadata > div:nth-child(1) > ytd-toggle-button-renderer:nth-child(2) > a:nth-child(1) > yt-formatted-string:nth-child(2)")))
        dislikes_attribute = dislikes_element.get_attribute('aria-label')
        script_element = self._wait.until(EC.presence_of_element_located((By.XPATH,"/html/body/script[1]")))

        if likes_element and likes_attribute:
            likes_attribute = likes_attribute.split()[0].replace(",","")
            if likes_attribute.isnumeric():
               data['likes'] = int(likes_attribute)
    
        if dislikes_element and dislikes_attribute and dislikes_attribute:
            dislikes_attribute = dislikes_attribute.split()[0].replace(",","")
            if dislikes_attribute.isnumeric():
               data['dislikes'] = int(dislikes_attribute)

        if "likes" not in data.keys():
            data['likes'] = -999
        if "dislikes" not in data.keys():
            data['dislikes'] = -999

        json_str = ""
        ytInitial = script_element.get_attribute("innerHTML").replace("var ytInitialPlayerResponse = ","")
        for i in range(len(ytInitial)):
            if ytInitial[i:i+8] == "var meta":
                break
            else:
                json_str += ytInitial[i]

        dump = json.loads(json_str[:len(json_str)-1])
        data['videoID'] = dump['videoDetails']['videoId']
        data['viewCount'] = dump['microformat']['playerMicroformatRenderer']['viewCount']
        data['category'] = dump['microformat']['playerMicroformatRenderer']['category']
        data['uploadDate'] = datetime.datetime.strptime(dump['microformat']['playerMicroformatRenderer']['uploadDate'],"%Y-%m-%d")
        return data

    def close(self):
        """
        Close Chrome Session 
        """
        self._driver.quit()
        print("Closed Chrome Session.")

def main():
    """
    Webscrape for meme videos on YouTube.
    Print Results. 
    """
    yt = YouTubeScraper('./chromedriver')
    print("Scraping...")
    result = yt.search(search_query="Nature", meta_data=True, save=True)
    yt.close()
    print(result)
    print("Web Scrape Complete!")
    
if __name__ == "__main__":
    main()