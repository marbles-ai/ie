from os import path
from PIL import Image
import numpy as np

from wordcloud import WordCloud
from wordcloud import STOPWORDS

def generate_wordcloud():
    d = path.dirname(__file__)

    # Read the text file containing the words we want to use
    text = open(path.join(d, 'file.txt')).read()

    # If we want the word cloud to be masked, use the mask image
    mask = np.array(Image.open(path.join(d, "mask.png")))

    # Words that we don't want to have in our graph
    stopwords = set(STOPWORDS)

    wordcloud = WordCloud(background_color="clear", max_words=100, mask=mask,
                          stopwords=stopwords)

    # Generate the wordcloud image
    wordcloud.generate(text)

    # Store the resulting file
    wordcloud.to_file(path.join(d, "background.png"))
