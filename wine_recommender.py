import pandas as pd
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def interpret_strength(user_text):
    """
    Interprets descriptive terms for alcohol strength or specific ABV ranges.
    Returns an ABV string like '11-12%', '12-13%', '13-14%', '14-15%'
    or None if nothing matched.
    """
    text = user_text.lower()

    # 1) Handle "less than X%"
    match_less = re.search(r"less\s+than\s+(\d+)%", text)
    if match_less:
        limit = int(match_less.group(1))
        if limit <= 12:
            return "11-12%"
        elif limit <= 13:
            return "12-13%"
        elif limit <= 14:
            return "13-14%"
        else:
            return "14-15%"

    # 2) Handle descriptive terms
    if any(word in text for word in ["strong", "heavy", "high"]):
        return "14-15%"
    if any(word in text for word in ["light", "low"]):
        return "11-12%"
    if "medium" in text:
        return "12-13%"

    # 3) Direct ABV input like "13-14%"
    match_abv = re.search(r"(\d{1,2}-\d{1,2}%)", text)
    if match_abv:
        return match_abv.group(1)

    return None

class WineRecommender:
    def __init__(self, csv_path):
        try:
            self.data = pd.read_csv(csv_path)
            logger.debug(f"CSV file '{csv_path}' loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
            raise e

        # Rename 'Colour of Wine' to 'Color' for consistency
        if "Colour of Wine" in self.data.columns:
            self.data.rename(columns={"Colour of Wine": "Color"}, inplace=True)
            logger.debug("Renamed 'Colour of Wine' to 'Color'.")
        elif "Color" not in self.data.columns:
            raise ValueError("CSV must contain either 'Color' or 'Colour of Wine' column.")

        # Check if necessary columns exist
        required_columns = ["Price", "Color", "Alcohol Level (ABV)", "Country", "Winery", "Name", "Vintage"]
        for column in required_columns:
            if column not in self.data.columns:
                raise ValueError(f"CSV must contain a '{column}' column.")
        logger.debug("All required columns are present.")

        # Filter out unrealistic ABV values
        self.data["Alcohol Level (ABV)"] = pd.to_numeric(self.data["Alcohol Level (ABV)"], errors='coerce')
        initial_count = len(self.data)
        self.data = self.data[self.data["Alcohol Level (ABV)"].between(5, 20)]
        filtered_count = len(self.data)
        logger.debug(f"Filtered out {initial_count - filtered_count} entries with unrealistic ABV values.")

        # Initialize steps
        self.steps = [
            {
                "key": "Color",
                "question": "What color wine do you prefer?",
                "options": ["Red", "White", "Rosé", "Sparkling"],
            },
            {
                "key": "AlcoholLevel",
                "question": "What is your preferred alcohol range?",
                "options": ["11-12%", "12-13%", "13-14%", "14-15%"]
            },
            {
                "key": "Country",
                "question": "Which country do you prefer?",
                "options": ["France", "Spain", "Italy", "Others"]
            },
            {
                "key": "PriceRange",
                "question": "Which price range do you want?",
                "options": ["$10-20", "$20-30", "$30-40", "$40-50"]
            },
        ]

        # Initialize criteria with all slots as None
        self.criteria = {
            "Color": None,
            "AlcoholLevel": None,
            "Country": None,
            "PriceRange": None,
        }

        # Track the current slot being prompted
        self.pending_slot = None

        # Define the fallback priority order
        # Exclude "PriceRange" from being relaxed
        self.fallback_order = ["AlcoholLevel", "Country", "Color"]

        # Track removed constraints during fallback
        self.removed_constraints = []

    def reset(self):
        """Reset all user preferences."""
        for slot in self.criteria:
            self.criteria[slot] = None
        self.pending_slot = None
        self.removed_constraints = []
        logger.debug("Session reset.")

    def handle_message(self, user_text):
        """Main logic to handle user messages."""
        user_text = user_text.strip()
        logger.debug(f"Handling message: '{user_text}'")

        # 1) Handle pending slot if any
        if self.pending_slot:
            validation = self.validate_slot_choice(user_text, self.pending_slot)
            if not validation["valid"]:
                step_info = self.get_step_by_key(self.pending_slot)
                logger.debug(f"Invalid input for '{self.pending_slot}': '{user_text}'")
                return {
                    "message": validation["error"],
                    "options": step_info["options"]
                }
            else:
                self.criteria[self.pending_slot] = validation["choice"]
                logger.debug(f"Set '{self.pending_slot}' to '{validation['choice']}'")
                self.pending_slot = None

        # 2) Parse free text to fill any slots
        self.parse_free_text(user_text)

        # 3) Count filled slots
        filled_count = sum(bool(v) for v in self.criteria.values())
        logger.debug(f"Filled slots: {self.criteria}")

        # 4) Determine next action based on filled slots
        if filled_count == 0:
            # Greet and ask the first preference
            first_step = self.steps[0]
            self.pending_slot = first_step["key"]
            logger.debug("No slots filled. Prompting first question.")
            return {
                "message": "Hi! How can I assist you today?\n" + first_step["question"],
                "options": first_step["options"]
            }

        # 5) If not all slots are filled, ask for the next unfilled slot
        if filled_count < len(self.criteria):
            next_step = self.find_unfilled_slot()
            if next_step:
                self.pending_slot = next_step["key"]
                logger.debug(f"Prompting next slot: '{next_step['key']}'")
                return {
                    "message": f"Got it. {next_step['question']}",
                    "options": next_step["options"]
                }

        # 6) If all slots are filled, attempt to filter and recommend
        df_result, removed = self.filter_data_with_fallback(self.data, self.criteria)
        self.removed_constraints = removed

        if df_result.empty:
            # No matches even after fallback
            c = self.criteria
            msg = (
                "No wines matched your preferences, even after relaxing some constraints.\n"
                f"(Color={c['Color'] or 'Any'}, ABV={c['AlcoholLevel'] or 'Any'}, "
                f"Country={c['Country'] or 'Any'}, Price={c['PriceRange'] or 'Any'})\n"
                "Try changing or removing a constraint (e.g., 'Change ABV to 13-14%' or 'Remove country filter')."
            )
            logger.debug("No matches found after fallback.")
            return {"message": msg, "options": []}
        else:
            # We have at least one match
            # Provide a list of up to 5 recommendations
            recommendations = df_result.head(5)
            rec_text = self.format_recommendations(recommendations)

            # If constraints were relaxed, inform the user
            if self.removed_constraints:
                removed_str = ", ".join(self.removed_constraints)
                rec_text += f"\n\n**Note**: We relaxed the following constraints to find these matches: {removed_str}."
                logger.debug(f"Relaxed constraints: {removed_str}")

            logger.debug(f"Recommendations:\n{rec_text}")
            return {
                "message": rec_text,
                "options": []
            }

    def parse_free_text(self, user_text):
        """Parse free-form user input to fill in any criteria."""
        text = user_text.lower()
        logger.debug(f"Parsing free text: '{text}'")

        # Attempt to fill AlcoholLevel
        if self.criteria["AlcoholLevel"] is None:
            abv_guess = interpret_strength(user_text)
            if abv_guess:
                self.criteria["AlcoholLevel"] = abv_guess
                logger.debug(f"AlcoholLevel set to '{abv_guess}'")

        # Attempt to fill Color
        if self.criteria["Color"] is None:
            if "red" in text:
                self.criteria["Color"] = "Red"
                logger.debug("Color set to 'Red'")
            elif "white" in text:
                self.criteria["Color"] = "White"
                logger.debug("Color set to 'White'")
            elif "rosé" in text or "rose" in text:
                self.criteria["Color"] = "Rosé"
                logger.debug("Color set to 'Rosé'")
            elif "sparkling" in text:
                self.criteria["Color"] = "Sparkling"
                logger.debug("Color set to 'Sparkling'")

        # Attempt to fill Country
        if self.criteria["Country"] is None:
            if "france" in text:
                self.criteria["Country"] = "France"
                logger.debug("Country set to 'France'")
            elif "spain" in text:
                self.criteria["Country"] = "Spain"
                logger.debug("Country set to 'Spain'")
            elif "italy" in text:
                self.criteria["Country"] = "Italy"
                logger.debug("Country set to 'Italy'")
            elif "other" in text or "others" in text:
                self.criteria["Country"] = "Others"
                logger.debug("Country set to 'Others'")

        # Attempt to fill PriceRange
        if self.criteria["PriceRange"] is None:
            for opt in ["$10-20", "$20-30", "$30-40", "$40-50"]:
                if opt.lower() in text:
                    self.criteria["PriceRange"] = opt
                    logger.debug(f"PriceRange set to '{opt}'")
                    break
            # Handle "under X" price
            match = re.search(r"under\s+\$?(\d+)", text)
            if match and self.criteria["PriceRange"] is None:
                num = int(match.group(1))
                if num <= 20:
                    self.criteria["PriceRange"] = "$10-20"
                elif num <= 30:
                    self.criteria["PriceRange"] = "$20-30"
                elif num <= 40:
                    self.criteria["PriceRange"] = "$30-40"
                else:
                    self.criteria["PriceRange"] = "$40-50"
                logger.debug(f"PriceRange set to based on 'under X': '{self.criteria['PriceRange']}'")

    def validate_slot_choice(self, user_text, slot_key):
        """Validate user input for a specific slot."""
        step_info = self.get_step_by_key(slot_key)
        if not step_info:
            logger.error(f"No step found for slot key: '{slot_key}'")
            return {"valid": False, "error": "Internal error. Please try again later."}

        valid_opts = step_info["options"]
        lower_opts = [opt.lower() for opt in valid_opts]
        t = user_text.lower().strip()

        # Handle numerical input (e.g., "1" for first option)
        if t.isdigit():
            idx = int(t) - 1
            if 0 <= idx < len(valid_opts):
                logger.debug(f"User selected option {idx + 1}: '{valid_opts[idx]}'")
                return {"valid": True, "choice": valid_opts[idx]}
            else:
                return {"valid": False, "error": f"Invalid choice. Please choose one of: {', '.join(valid_opts)}"}

        # Handle direct match
        if t in lower_opts:
            i = lower_opts.index(t)
            logger.debug(f"User selected option: '{valid_opts[i]}'")
            return {"valid": True, "choice": valid_opts[i]}

        # Handle partial matches or common misspellings
        for opt in valid_opts:
            if opt.lower().startswith(t):
                logger.debug(f"User partially matched option: '{opt}'")
                return {"valid": True, "choice": opt}

        # If no valid option matched
        return {
            "valid": False,
            "error": f"I didn't understand. Please choose one of: {', '.join(valid_opts)}"
        }

    def get_step_by_key(self, slot_key):
        """Retrieve step information based on slot key."""
        for s in self.steps:
            if s["key"] == slot_key:
                return s
        return None

    def find_unfilled_slot(self):
        """Find the next unfilled slot based on the defined order."""
        for step in self.steps:
            if self.criteria[step["key"]] is None:
                return step
        return None

    # -------------------------------------------------------------------------
    # Filtering logic
    # -------------------------------------------------------------------------
    def strict_filter_data(self, df, c):
        """Apply all current criteria to filter the DataFrame."""
        filt = df.copy()

        # Filter by Color
        color = c["Color"]
        if color:
            filt = filt[filt["Color"].str.lower() == color.lower()]
            logger.debug(f"Filtered by Color: '{color}' - {len(filt)} wines found.")

        # Filter by Alcohol Level
        abv_choice = c["AlcoholLevel"]
        if abv_choice:
            abv_range = abv_choice.replace('%', '').split('-')
            if len(abv_range) == 2:
                try:
                    abv_min, abv_max = float(abv_range[0]), float(abv_range[1])
                    filt = filt[(filt["Alcohol Level (ABV)"] >= abv_min) &
                                (filt["Alcohol Level (ABV)"] <= abv_max)]
                    logger.debug(f"Filtered by Alcohol Level: '{abv_choice}' - {len(filt)} wines found.")
                except ValueError:
                    logger.error(f"Invalid ABV range: {abv_range}")
                    return pd.DataFrame()

        # Filter by Country
        ctry = c["Country"]
        if ctry:
            if ctry.lower() == "others":
                filt = filt[~filt["Country"].str.lower().isin(["france", "spain", "italy"])]
                logger.debug(f"Filtered by Country: 'Others' - {len(filt)} wines found.")
            else:
                filt = filt[filt["Country"].str.lower() == ctry.lower()]
                logger.debug(f"Filtered by Country: '{ctry}' - {len(filt)} wines found.")

        # Filter by Price Range
        price = c["PriceRange"]
        if price:
            prange = price.replace('$', '').split('-')
            if len(prange) == 2:
                try:
                    pmin, pmax = float(prange[0]), float(prange[1])
                    # Clean and convert Price column
                    pcol = filt["Price"].astype(str).str.replace('[\\$,€]', '', regex=True).str.replace(',', '')
                    pcol = pd.to_numeric(pcol, errors='coerce')
                    filt["PriceNumeric"] = pcol
                    filt = filt[(filt["PriceNumeric"] >= pmin) & (filt["PriceNumeric"] <= pmax)]
                    logger.debug(f"Filtered by Price Range: '{price}' - {len(filt)} wines found.")
                except ValueError:
                    logger.error(f"Invalid Price range: {prange}")
                    return pd.DataFrame()

        return filt

    def filter_data_with_fallback(self, df, c):
        """
        Attempt to filter data with all criteria.
        If no match, relax constraints based on fallback_order.
        Returns the filtered DataFrame and a list of removed constraints.
        """
        # 1) Attempt strict filtering
        df_strict = self.strict_filter_data(df, c)
        if not df_strict.empty:
            logger.debug("Strict filtering successful.")
            return df_strict, []

        # 2) Attempt fallback by removing constraints in fallback_order
        temp_criteria = c.copy()
        removed = []

        for slot in self.fallback_order:
            if temp_criteria[slot] is not None:
                # Remove this constraint temporarily
                removed.append(slot)
                temp_criteria[slot] = None
                df_partial = self.strict_filter_data(df, temp_criteria)
                if not df_partial.empty:
                    logger.debug(f"Fallback: Removed '{slot}' constraint to find matches.")
                    return df_partial, removed

        # 3) No matches found even after fallback
        logger.debug("No matches found after fallback.")
        return pd.DataFrame(), removed

    # -------------------------------------------------------------------------
    # Recommendation Formatting
    # -------------------------------------------------------------------------
    def format_recommendations(self, df):
        """Format multiple recommendation messages based on the DataFrame."""
        rec_text = "Based on your current preferences, here are some suggestions:\n\n"
        for idx, row in df.iterrows():
            winery = row.get("Winery", "Unknown Winery")
            country = row.get("Country", "Unknown Country")
            name = row.get("Name", "Unnamed Wine")
            vintage = row.get("Vintage", "N/A")
            abv = row.get("Alcohol Level (ABV)", "N/A")
            price = row.get("Price", "N/A")

            # Validate and format alcohol level
            try:
                abv_float = float(abv)
                if abv_float < 5 or abv_float > 20:  # Define realistic ABV range
                    abv = "N/A"
            except:
                abv = "N/A"

            # Format vintage if it's numeric
            if pd.notnull(vintage):
                try:
                    vintage = int(vintage)
                except ValueError:
                    vintage = vintage

            rec_text += (
                f"{idx + 1}. Winery: {winery}, {country}\n"
                f"   {name} {vintage}\n"
                f"   {abv}% Alc./vol.\n"
                f"   ${price}\n\n"
            )

        # Add further filtering options
        rec_text += (
            "You can further refine your selection based on Appellation or Taste.\n"
            "For example:\n"
            "- **Appellation**:\n"
            "   - *Red*: Blend, Merlot, Bordeaux, Pinot\n"
            "   - *White*: Blend, Sauvignon, Bourgogne\n"
            "- **Taste**: Fruity, Dry, Sharp\n\n"
            "Please let me know if you'd like to apply any additional filters."
        )

        return rec_text

    def format_recommendation(self, row):
        """Format a single recommendation message based on the DataFrame row."""
        winery = row.get("Winery", "Unknown Winery")
        country = row.get("Country", "Unknown Country")
        name = row.get("Name", "Unnamed Wine")
        vintage = row.get("Vintage", "N/A")
        abv = row.get("Alcohol Level (ABV)", "N/A")
        price = row.get("Price", "N/A")

        # Validate and format alcohol level
        try:
            abv_float = float(abv)
            if abv_float < 5 or abv_float > 20:
                abv = "N/A"
        except:
            abv = "N/A"

        # Format vintage if it's numeric
        if pd.notnull(vintage):
            try:
                vintage = int(vintage)
            except ValueError:
                vintage = vintage

        rec_text = (
            f"Winery: {winery}, {country}\n"
            f"{name} {vintage}\n"
            f"{abv}% Alc./vol.\n"
            f"${price}\n"
        )

        return rec_text


    
    