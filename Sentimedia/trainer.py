import pandas as pd
import numpy as np
import string
# from nltk.corpus import wordnet as wn
# from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib
import pickle

def get_data():
    # Returns X and y datasets to be used for training

    # Load reviews and business json files
    reviews = pd.read_json('Sentimedia/data/yelp_academic_dataset_review.json', lines=True, nrows=300000)
    business = pd.read_json('Sentimedia/data/yelp_academic_dataset_business.json', lines=True)
    
    # Filter business df to only contain open restaurants
    df_restaurants = business.copy()
    df_restaurants = df_restaurants[df_restaurants.categories.notna()]
    df_restaurants = df_restaurants[df_restaurants.categories.str.contains("Restaurants")]
    
    # Filter all restaurants not located in Boston nor Westerville
    df_restaurants = df_restaurants[(df_restaurants.city != 'Boston') & (df_restaurants.city != 'Westerville')]
    df_restaurants = df_restaurants[df_restaurants.is_open == 1]
    df = reviews.merge(df_restaurants, on='business_id')
    
    return df.text, df.stars_x

def clean_text(s):
    
    # Remove punctuation from text
    s = s.translate(str.maketrans('', '', string.punctuation))
    
    # Lowercase all words
    s = s.lower()
    
    # Remove numbers from text
    s = ''.join([i for i in s if not i.isdigit()])
    
    # Remove stopwords from analysis
    stop_words = {"i", "ive",	"me",	"my",	"myself",	"we",	"our",	"ours",	"ourselves",	"you",	"you're",	"you've",	"you'll",	"you'd",	"your",	"yours",	"yourself",	"yourselves",	"he",	"him",	"his",	"himself",	"she",	"she's",	"her",	"hers",	"herself",	"it",	"it's",	"its",	"itself",	"they",	"them",	"their",	"theirs",	"themselves",	"what",	"which",	"who",	"whom",	"this",	"that",	"that'll",	"these",	"those",	"am",	"is",	"are",	"was",	"were",	"be",	"been",	"being",	"have",	"has",	"had",	"having",	"do",	"does",	"did",	"doing",	"a",	"an",	"the",	"and",	"but",	"if",	"or",	"because",	"as",	"until",	"while",	"of",	"at",	"by",	"for",	"with",	"about",	"against",	"between",	"into",	"through",	"during",	"before",	"after",	"above",	"below",	"to",	"from",	"up",	"down",	"in",	"out",	"on",	"off",	"over",	"under",	"again",	"further",	"then",	"once",	"here",	"there",	"when",	"where",	"why",	"how",	"all",	"any",	"both",	"each",	"few",	"more",	"most",	"other",	"some",	"such",	"no",	"nor",	"not",	"only",	"own",	"same",	"so",	"than",	"too",	"very",	"s",	"t",	"can",	"will",	"just",	"don",	"don't",	"should",	"should've",	"now",	"d",	"ll",	"m",	"o",	"re",	"ve",	"y",	"ain",	"aren",	"aren't",	"couldn",	"couldn't",	"didn",	"didn't",	"doesn",	"doesn't",	"hadn",	"hadn't",	"hasn",	"hasn't",	"haven",	"haven't",	"isn",	"isn't",	"ma",	"mightn",	"mightn't",	"mustn",	"mustn't",	"needn",	"needn't",	"shan",	"shan't",	"shouldn",	"shouldn't",	"wasn",	"wasn't",	"weren",	"weren't",	"won",	"won't",	"wouldn",	"wouldn't"}
    # stop_words = set(stopwords.words('english')) 
    word_tokens = word_tokenize(s) 
    lst = [w for w in word_tokens if not w in stop_words]
    txt = ''
    for w in lst:
        txt = txt + w + ' '
    
    return txt

def binary_review(x):
    if x >= 4:
        return 'positive'
    return 'negative'

def preprocess_data(X,y):

    X = X.map(clean_text)
    y = y.map(binary_review)

    return X, y

def train_model(X,y):
    #Returns a trained model

    # Vectorize data
    vectorizer = CountVectorizer()
    X_bow = vectorizer.fit_transform(X)
    
    # Save vectorizer dictionary for predictions
    feature_path = 'feature.pkl'
    with open(feature_path, 'wb') as fw:
        pickle.dump(vectorizer.vocabulary_, fw)
    
    # Initialize Multinomial NB model
    nb_model = MultinomialNB()
    
    # Train model on dataset
    nb_model.fit(X_bow, y)
    
    return nb_model

def save_model(model):
    joblib.dump(model, 'model.joblib')
    return

def get_model():
    model = joblib.load('model.joblib')
    return model

def get_dicts(rest_name, review_df):
    # Returns two dicts with most used words
    
    # Selecting reviews from specific business inside reviews dataframe (json file)
    review = review_df[review_df['name'] == rest_name].text
    
    # Data cleaning and removing stop words
    review = review.map(clean_text)
    
    # Loading vectorizer vocabulary from training
    feature_path = 'feature.pkl'
    vectorizer = CountVectorizer(decode_error="replace", vocabulary=pickle.load(open(feature_path, "rb")))

    # Bag of words modelling
    reviews_bow = vectorizer.transform(review)
    
    # Reviews rating prediction
    model = get_model()
    reviews_predict = model.predict(reviews_bow)
    
    # Creating tmp dataframe
    df = pd.DataFrame(review)
    df['review'] = reviews_predict
    
    # Positive words
    positive = df[df.review == 'positive'].text
    positive = vectorizer.transform(positive)
    p = pd.DataFrame(positive.toarray(),columns = vectorizer.get_feature_names())
    p_dict_10 = dict(p.sum().sort_values(ascending=False).head(10))
    p_dict_30 = dict(p.sum().sort_values(ascending=False).head(30))
    
    # Negative words
    negative = df[df.review == 'negative'].text
    negative = vectorizer.transform(negative)
    n = pd.DataFrame(negative.toarray(),columns = vectorizer.get_feature_names())
    n_dict_10 = dict(n.sum().sort_values(ascending=False).head(10))
    n_dict_30 = dict(n.sum().sort_values(ascending=False).head(30))
    
    # Positive words returned first!
    return p_dict_10, p_dict_30, n_dict_10, n_dict_30

def live_demo(text):
    # Returns a prediction for live demonstration with a new set of reviews

    # Preprocessing text
    text = pd.Series(text)
    text = text.map(clean_text)
    feature_path = 'feature.pkl'
    vectorizer = CountVectorizer(decode_error="replace", vocabulary=pickle.load(open(feature_path, "rb")))
    text_bow = vectorizer.transform(text)
    
    # Reviews rating prediction
    model = get_model()
    text_predict = model.predict(text_bow)

    return text_predict

def update_data(new):
    # Updates the dataset to include new reviews

    # Merging old with new entries
    old = pd.read_pickle("review_data.pkl")
    # new = pd.read_csv(csv)
    updated = pd.concat([old, new], ignore_index=True)
    
    # Saving to a pickle file
    updated.to_pickle("review_data.pkl", protocol=2)

    return

if __name__ == "__main__":
    X, y = get_data()
    X, y = preprocess_data(X,y)
    model = train_model(X,y)
    save_model(model)
    print('Model saved locally!')