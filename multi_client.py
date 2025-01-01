#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 01:25:42 2024

@author: jean
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 21 20:00:00 2024

Example multi-client approach using WineRecommender.
"""

import pandas as pd
from wine_recommender import WineRecommender

class MultiUserRecommenderService:
    """
    A service that manages multiple WineRecommender instances,
    one for each user/session ID.5
    """
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.sessions = {}  # Dictionary: user_id -> WineRecommender
    
    def get_recommender(self, user_id):
        """
        Returns the WineRecommender for the given user_id.
        If none exists, create a new one.
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = WineRecommender(self.csv_path)
        return self.sessions[user_id]
    
    def reset_recommender(self, user_id):
        """
        Clear the user's WineRecommender instance, forcing a fresh Q&A flow.
        """
        self.sessions[user_id] = WineRecommender(self.csv_path)
        return self.sessions[user_id]

# Quick test example
if __name__ == "__main__":
    service = MultiUserRecommenderService("enriched_wine_data_safari.csv")
    
    alice_recommender = service.get_recommender("alice")
    print(alice_recommender.get_current_question())  # Q1

    bob_recommender = service.get_recommender("bob")
    print(bob_recommender.get_current_question())    # Q1 (separate session)55