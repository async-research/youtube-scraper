from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd 
import time, json, datetime, os


class YouTubeScraper:
    def __init__(self, driver_path, headless=True,  wait=30):
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
  
        self._driver = webdriver.Chrome(options=self._chrome_options, executable_path=driver_path)
        self._driver.maximize_window()
        self._wait = WebDriverWait(self._driver, wait)

    def search(self, search_query='rickroll', meta_data=False, save=False, directory='scrapes', scale=0):
        """
        Search for videos on YouTube 

        Paramerters
            search_query: a str type containing search query for YouTube. 
            meta_data: a boolean type,  True : return  a list of dcts with metadata.
                                        False: return a list of videoIDs
            comments: generate a csv of comments in a video.
            save: a boolean type,  True: save DataFrame to local dir as a .csv file. 
            seachScale: a int type, Determines the scale of how many videos are visible to 
                  Chrome by scrolling by this amount.
            commentScale: a int type, Determines the scale of how many comments are visible.
        Returns:
            A list of videoIDs  or panda DataFrame containing metadata of each videoID

        """
        cur_dir = os.getcwd()
        path = os.path.join(cur_dir, directory)


        if not os.path.isdir(path):
            os.mkdir(path)

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

        if meta_data and len(videos) > 0:
            videos_dataframe = self.create_search_dataframe(videos) 
            if save and not videos_dataframe.empty:
                videos_dataframe.to_csv(os.path.join(path,f"query_{search_query.replace(' ','-')}_results.csv"))
                print("Successfully saved search results DataFrame!")

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

    def get_comments(self, videoID, directory="comments", save=False, scale=3):
        comments =[]
        cur_dir = os.getcwd()
        path = os.path.join(cur_dir, directory)

        if not os.path.isdir(path):
            os.mkdir(path)

        url = "https://www.youtube.com/watch?v="+videoID
        self._driver.get(url)  
        for i in range(scale): 
            time.sleep(1)
            self._wait.until(EC.visibility_of_element_located((By.TAG_NAME, "body"))).send_keys(Keys.PAGE_DOWN) 

        try:
            for comment in self._wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "style-scope ytd-comment-renderer"))):
                post = {}
                post['likes'] = 0 
                post['author'] = "" 
                post['content'] = ""
            
                post['author'] = comment.find_element_by_id("author-text").text
                if post['author'] == "":
                    post['author'] = comment.find_element_by_id("text").text
                post['content'] = comment.find_element_by_id("content-text").text
                post['likes']  = comment.find_element_by_id("vote-count-middle").text
                comments.append(post)
                print(post)
            comments_df = pd.DataFrame(comments, columns=['author','likes','content'])
            print(comments_df)

        except Exception as e:
            print(f"Unable to retrieve comments from {videoID}.")
        else:
            if save:
                save_path = os.path.join(path, f"videoID_{videoID}.csv")
                comments_df.to_csv(save_path)


    def create_search_dataframe(self, videos):
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
        return pd.DataFrame(results, columns=['videoID','likes','dislikes','viewCount','uploadDate','category'])

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
    yt = YouTubeScraper('./chromedriver', headless=False)
    print("Scraping...")
    result = yt.search(search_query="Nature", meta_data=True, save=True)
    for i in range(len(result['videoID'])):
        yt.get_comments(result['videoID'][i], save=True)
      
   
    yt.close()
    print(result)
    print("Web Scrape Complete!")
    
if __name__ == "__main__":
    main()