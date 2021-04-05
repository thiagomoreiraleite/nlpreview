import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
import spacy
import scattertext as sct
from wordcloud import WordCloud, STOPWORDS
from Sentimedia.trainer import get_dicts
import folium
import folium.plugins as plugins
import pickle

import streamlit as st
from pyecharts.charts import WordCloud
from pyecharts import options as opts
from streamlit_echarts import st_pyecharts
from pyecharts.charts import Bar


def get_bus_data():
    bus_data_path = 'Sentimedia/data/yelp_academic_dataset_business.json'
    df = pd.read_json(bus_data_path, lines=True)
    df_open = df[df['is_open']==1]

    df_restaurants = df_open.copy()
    df_restaurants = df_restaurants[df_restaurants.categories.notna()]
    df_restaurants = df_restaurants[df_restaurants.categories.str.contains("Restaurants")]

    # df_rest_filter = df_restaurants[(df_restaurants.city == 'Boston') | (df_restaurants.name == 'Westerville')].head(1000)
    df_rest_filter_city = df_restaurants[(df_restaurants.city == 'Boston') & (df_restaurants['review_count'] < 100) & (df_restaurants['review_count'] > 80) ].head(20)
    df_rest_filter_default = df_restaurants[(df_restaurants.city == 'Boston') & (df_restaurants.name == 'Parish Cafe and Bar') | (df_restaurants.name == 'Bistro du Midi')]
    df_rest_filter = pd.concat([df_rest_filter_city, df_rest_filter_default])

    df_rest_filter.to_pickle("bus_data.pkl", protocol=2)
    print('Business data saved')

    return df_rest_filter


def get_review_data():
    df_rest_filter = pd.read_pickle("bus_data.pkl")
    review_json_path = 'Sentimedia/data/yelp_academic_dataset_review.json'
    size = 500000
    review = pd.read_json(review_json_path, lines=True,
                      dtype={'review_id':str,'user_id':str,
                             'business_id':str,'stars':int,
                             'date':str,'text':str,'useful':int,
                             'funny':int,'cool':int},
                      chunksize=size)

    chunk_list = []
    for chunk_review in review:
        chunk_review = chunk_review.rename(columns={'stars': 'review_stars'})
        chunk_merged = pd.merge(df_rest_filter, chunk_review, on='business_id', how='inner')
        print(f"{chunk_merged.shape[0]} out of {size:,} related reviews")
        chunk_list.append(chunk_merged)

    df_review = pd.concat(chunk_list, ignore_index=True, join='outer', axis=0)
    df_review = df_review[['name','city','review_stars','text', 'business_id']]

    df_review.to_pickle("review_data.pkl", protocol=2)
    print('Review data saved')

    return df_review

######## folium_map ######
def loc_city(city_name):
    df_rest_filter = pd.read_pickle("bus_data.pkl")
    city = df_rest_filter[df_rest_filter['city'] == city_name].sort_values('stars')
    lon = city['longitude'].median()
    lat = city['latitude'].median()
    data=[]
    stars_list=list(city['stars'].unique())
    for star in stars_list:
        subset=city[city['stars']==star]
        data.append(subset[['latitude','longitude','name','stars']].values.tolist())
    data = [item for sublist in data for item in sublist]
    return data, lon, lat

def rest_coord(rest_name,city_name):
    df_rest_filter = pd.read_pickle("bus_data.pkl")
    rest_data = df_rest_filter[(df_rest_filter.name == rest_name)&(df_rest_filter.city == city_name)][['latitude','longitude']].values.tolist()
    return rest_data

def make_folium(city_name,rest_name,rating):
    data, lon, lat = loc_city(city_name)
    rest_data = rest_coord(rest_name,city_name)
    m = folium.Map(location=[lat, lon], tiles="OpenStreetMap", zoom_start=11)
    marker_cluster = folium.plugins.MarkerCluster().add_to(m)
    for point in range(0, len(data)):
        if data[point][:-2] in rest_data:
            folium.Marker(data[point][:-2], icon=folium.Icon(color='red',icon='glyphicon glyphicon-cutlery'), popup=rest_name).add_to(m)
        if data[point][-1] > rating:
            folium.Marker(data[point][:-2],popup=f'{str(data[point][-2])}, {str(data[point][-1])} stars').add_to(marker_cluster)
    return m

#interact(make_folium,city_name="Orlando",rest_name='Subway',rating=(0,5,0.5))



##### HTML- NLP #######
def good_bad_review(x):
    if x >= 4:
        return 'good'
    return 'bad'

def get_rest_reviews(rest_name, city_name):
    df_review = pd.read_pickle("review_data.pkl")
    rest_reviews = df_review[(df_review.name == rest_name)&(df_review.city == city_name)]
    rest_reviews['class'] = rest_reviews.review_stars.map(good_bad_review)
    return rest_reviews

def get_sct_html(rest_name, city_name):
    rest_reviews = get_rest_reviews(rest_name, city_name)
    nlp = spacy.load('en_core_web_sm')
    corpus = sct.CorpusFromPandas(rest_reviews,
                             category_col='class',
                             text_col='text',
                             nlp=nlp).build()
    html = sct.produce_scattertext_explorer(corpus,
         category='good',
         category_name='Positive',
         not_category_name='Negative',
         width_in_pixels=900,
         metadata=rest_reviews['class'])
    return open("rest_reviews-Vis.html", 'wb').write(html.encode('utf-8'))



###### WordCloud #####
# def make_wordcloud(rest_name):
#     p_dict_10, p_dict_30, n_dict_10, n_dict_30 = get_dicts(rest_name, pd.read_pickle("review_data.pkl"))

#     wordcloud_good = WordCloud(background_color="white").generate_from_frequencies(p_dict_30)
#     wordcloud_bad = WordCloud(background_color="white").generate_from_frequencies(n_dict_30)

#     fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 10))

#     axes[0].imshow(wordcloud_good, interpolation='bilinear')
#     axes[0].axis("off")

#     axes[1].imshow(wordcloud_bad, interpolation='bilinear')
#     axes[1].axis("off")

#     return fig.tight_layout()

def make_wordcloud_interactive(rest_name, stop_list_pos, stop_list_neg):
    p_dict_10, p_dict_30, n_dict_10, n_dict_30 = get_dicts(rest_name, pd.read_pickle("review_data.pkl"))
    data_positive = [(k, str(v)) for k, v in p_dict_30.items() if k not in stop_list_pos]
    c_positive = (
        WordCloud()
        .add(series_name="frequent words", data_pair=data_positive, word_size_range=[15, 70])
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=f'Positive Reviews - {rest_name}', subtitle="Most frequent words", title_textstyle_opts=opts.TextStyleOpts(font_size=25)
            ),
            tooltip_opts=opts.TooltipOpts(is_show=True),
        )
    )

    data_negative = [(k, str(v)) for k, v in n_dict_30.items() if k not in stop_list_neg]
    c_negative = (
        WordCloud()
        .add(series_name="frequent words", data_pair=data_negative, word_size_range=[15, 70])
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=f'Negative Reviews - {rest_name}', subtitle="Most frequent words", title_textstyle_opts=opts.TextStyleOpts(font_size=25)
            ),
            tooltip_opts=opts.TooltipOpts(is_show=True),
        )
    )

    return c_positive, c_negative, data_positive, data_negative

####### Barplot ######
# def make_barplot(rest_name):
#     p_dict_10, p_dict_30, n_dict_10, n_dict_30 = get_dicts(rest_name, pd.read_pickle("review_data.pkl"))
#     fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10, 5))
#     plt.suptitle('Why the restaurant is rated bad or good')
#     fig.text(0.5, 0, 'Words', ha='center')
#     fig.text(0, 0.5, 'Frequency', va='center', rotation='vertical')
#     axes[0].bar(n_dict_10.keys(),n_dict_10.values(), color='r', label='negative')
#     axes[0].tick_params(labelrotation=45)
#     axes[0].legend()
#     axes[1].bar(p_dict_10.keys(),p_dict_10.values(), color='b', label='positive')
#     axes[1].tick_params(labelrotation=45)
#     axes[1].legend()
#     return fig.tight_layout()

def make_barplot_interactive(rest_name, stop_list_pos, stop_list_neg):
    p_dict_10, p_dict_30, n_dict_10, n_dict_30 = get_dicts(rest_name, pd.read_pickle("review_data.pkl"))
    data_positive = [(k, str(v)) for k, v in p_dict_10.items() if k not in stop_list_pos]
    words_list_pos = [x[0] for x in data_positive]
    freq_list_pos = [x[1] for x in data_positive]
    data_negative = [(k, str(v)) for k, v in n_dict_10.items() if k not in stop_list_neg]
    words_list_neg = [x[0] for x in data_negative]
    freq_list_neg = [x[1] for x in data_negative]
    b_pos = (
        Bar()
        .add_xaxis(words_list_pos)
        .add_yaxis(
            "Frequency found in reviews", freq_list_pos, color = "#2f8232"
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="Positive Reviews", title_textstyle_opts=opts.TextStyleOpts(font_size=18), subtitle=f'{rest_name.upper()}', subtitle_textstyle_opts=opts.TextStyleOpts(font_size=18)
            )
        )
    )
    b_neg = (
        Bar()
        .add_xaxis(words_list_neg)
        .add_yaxis(
            "Frequency found in reviews", freq_list_neg
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="Negative Reviews", title_textstyle_opts=opts.TextStyleOpts(font_size=18), subtitle=f'{rest_name.upper()}', subtitle_textstyle_opts=opts.TextStyleOpts(font_size=18)
            )
        )
    )
    return b_pos, b_neg




if __name__ == "__main__":
    get_bus_data()
    get_review_data()
