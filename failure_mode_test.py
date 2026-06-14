""" This is for milestone 5 triggers """


# Trigger search_listings returning zero results. 
# Run this directly from the terminal:
from tools import search_listings
print(search_listings('designer ballgown', size='XXS', max_price=5))
print() 

# Trigger suggest_outfit with an empty wardrobe:
from tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
print() 

#Trigger create_fit_card with an empty outfit string:
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))