import requests
import json
import os
from .models import CarDealer, DealerReview
from requests.auth import HTTPBasicAuth
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, SentimentOptions


# Function for making HTTP GET requests
def get_request(url, api_key=False, **kwargs):
    print(f"GET from {url}")
    if api_key:
        # Basic authentication GET
        try:
            response = requests.get(url, headers={'Content-Type': 'application/json'},
                                    params=kwargs, auth=HTTPBasicAuth('apikey', api_key))
        except:
            print("An error occurred while making GET request. ")
    else:
        # No authentication GET
        try:
            response = requests.get(url, headers={'Content-Type': 'application/json'},
                                    params=kwargs)
        except:
            print("An error occurred while making GET request. ")

    # Retrieving the response status code and content
    status_code = response.status_code
    print(f"With status {status_code}")
    json_data = json.loads(response.text)

    return json_data


# Function for making HTTP POST requests
def post_request(url, json_payload, **kwargs):
    print(f"POST to {url}")
    try:
        response = requests.post(url, params=kwargs, json=json_payload)
    except:
        print("An error occurred while making POST request. ")
    status_code = response.status_code
    print(f"With status {status_code}")

    return response


# Gets all dealers from the Cloudant DB with the Cloud Function get-dealerships
# Gets all dealers from the Cloudant DB with the Cloud Function get-dealerships
def get_dealers_from_cf(url):
    results = []
    try:
        json_result = get_request(url)
        
        # Assuming json_result is a list of dealers
        for dealer in json_result:
            # Access elements of each dealer dictionary using keys
            dealer_obj = CarDealer(
                address=dealer.get("address", ""),
                city=dealer.get("city", ""),
                full_name=dealer.get("full_name", ""),
                id=dealer.get("id", ""),
                lat=dealer.get("lat", ""),
                long=dealer.get("long", ""),
                short_name=dealer.get("short_name", ""),
                st=dealer.get("st", ""),
                state=dealer.get("state", ""),
                zip=dealer.get("zip", "")
            )
            results.append(dealer_obj)
    except Exception as e:
        print(f"An error occurred while fetching dealer data: {str(e)}")

    return results



# Gets a single dealer from the Cloudant DB with the Cloud Function get-dealerships
# Requires the dealer_id parameter with only a single value
def get_dealer_by_id(url, dealer_id):
    # Call get_request with the dealer_id param
    json_result = get_request(url, dealerId=dealer_id)

    if isinstance(json_result, dict) and "entries" in json_result and isinstance(json_result["entries"], list) and len(json_result["entries"]) > 0:
        dealer = json_result["entries"][0]
        dealer_obj = CarDealer(address=dealer.get("address", ""), city=dealer.get("city", ""), full_name=dealer.get("full_name", ""),
                               id=dealer.get("id", ""), lat=dealer.get("lat", ""), long=dealer.get("long", ""),
                               short_name=dealer.get("short_name", ""),
                               st=dealer.get("st", ""), state=dealer.get("state", ""), zip=dealer.get("zip", ""))
        return dealer_obj
    else:
        print("Failed to retrieve dealer information.")
        return None


# Gets all dealers in the specified state from the Cloudant DB with the Cloud Function get-dealerships
def get_dealers_by_state(url, state):
    results = []
    # Call get_request with the state param
    json_result = get_request(url, state=state)
    dealers = json_result["body"]["docs"]
    # For each dealer in the response
    for dealer in dealers:
        # Create a CarDealer object with values in `doc` object
        dealer_obj = CarDealer(address=dealer["address"], city=dealer["city"], full_name=dealer["full_name"],
                               id=dealer["id"], lat=dealer["lat"], long=dealer["long"],
                               short_name=dealer["short_name"],
                               st=dealer["st"], state=dealer["state"], zip=dealer["zip"])
        results.append(dealer_obj)

    return results


# Gets all dealer reviews for a specified dealer from the Cloudant DB
# Uses the Cloud Function get_reviews
def get_dealer_reviews_from_cf(url, dealer_id):
    results = []

    # Perform a GET request with the specified dealer id
    json_result = get_request(url, dealerId=dealer_id)

    if json_result and isinstance(json_result, dict) and "body" in json_result:
        reviews_data = json_result["body"]
        if "data" in reviews_data and isinstance(reviews_data["data"], dict) and "docs" in reviews_data["data"]:
            # Get all review data from the response
            reviews = reviews_data["data"]["docs"]
            # For every review in the response
            for review in reviews:
                try:
                    # Create a DealerReview object from the data
                    # These values must be present
                    review_content = review.get("review", "")
                    id = review.get("_id", "")
                    name = review.get("name", "")
                    purchase = review.get("purchase", False)
                    dealership = review.get("dealership", "")

                    # These values may be missing
                    car_make = review.get("car_make", None)
                    car_model = review.get("car_model", None)
                    car_year = review.get("car_year", None)
                    purchase_date = review.get("purchase_date", None)

                    # Creating a review object
                    review_obj = DealerReview(
                        dealership=dealership, id=id, name=name,
                        purchase=purchase, review=review_content, car_make=car_make,
                        car_model=car_model, car_year=car_year, purchase_date=purchase_date
                    )

                except KeyError:
                    print("Something is missing from this review. Using default values.")
                    # Creating a review object with some default values
                    review_obj = DealerReview(
                        dealership=dealership, id=id, name=name, purchase=purchase, review=review_content)

                # Analysing the sentiment of the review object's review text and saving it to the object attribute "sentiment"
                review_obj.sentiment = analyze_review_sentiments(review_obj.review)
                print(f"sentiment: {review_obj.sentiment}")

                # Saving the review object to the list of results
                results.append(review_obj)

    return results
