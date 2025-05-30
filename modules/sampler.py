import random
from typing import List

from modules.models import InputData, DemoData

class Sampler:
    """
    A sampler for retrieving demo examples based on input data criteria.
    The demo data list is provided at instantiation.
    """
    _all_demos: List[DemoData] # Type hint for the instance variable

    def __init__(self, all_demo_data: List[DemoData]):
        """
        Initializes the Sampler with a pre-loaded list of DemoData objects.

        Args:
            all_demo_data: A list of DemoData objects.
        
        Raises:
            ValueError: If the provided all_demo_data list is empty or None.
        """
        if not all_demo_data: # Check if the list is None or empty
            raise ValueError("The provided 'all_demo_data' list cannot be None or empty.")
        
        # Store a copy to ensure the Sampler's internal list isn't affected by external modifications
        # to the original list after instantiation (promoting immutability of the Sampler's state).
        self._all_demos = list(all_demo_data) 
        
        print(f"Sampler initialized with {len(self._all_demos)} demo items.")

    def retrieve_demos(self, input_data: InputData, num_examples: int) -> List[DemoData]:
        """
        Retrieves a list of demo examples based on hierarchical filtering and random selection.

        The selection priority is:
        1. Randomly from demos matching both input_data.region and input_data.item_category.
        2. Randomly from remaining demos matching input_data.region only.
        3. Randomly from remaining demos not matching input_data.region.

        Args:
            input_data: The InputData object for the current item being processed.
            num_examples: The desired number of demo examples to retrieve.

        Returns:
            A list of DemoData objects, up to num_examples.
        """
        if num_examples <= 0:
            return []
        if not self._all_demos: # Should ideally be caught by constructor
            return []

        selected_demos: List[DemoData] = []
        
        # Tier 1: Match region and item_category (Set B logic)
        pool_b = [
            demo for demo in self._all_demos
            if demo.region == input_data.region and demo.item_category == input_data.item_category
        ]
        random.shuffle(pool_b)

        # Tier 2: Match region only (Set A Prime: region match, different item_category)
        pool_a_prime = [
            demo for demo in self._all_demos
            if demo.region == input_data.region and demo.item_category != input_data.item_category
        ]
        random.shuffle(pool_a_prime)

        # Tier 3: No region match (Set C Prime: different region)
        pool_c_prime = [
            demo for demo in self._all_demos
            if demo.region != input_data.region
        ]
        random.shuffle(pool_c_prime)

        # Fill selected_demos from pools in order of priority
        # The pools are defined to be disjoint, so we don't need to track selected IDs
        # to avoid duplicates when moving between these specific pre-defined pools.
        
        for demo_pool in [pool_b, pool_a_prime, pool_c_prime]:
            for demo in demo_pool:
                if len(selected_demos) < num_examples:
                    # Check if this specific demo instance is already selected
                    # This is a safeguard if _all_demos could somehow contain duplicate objects
                    # or if future logic makes pools overlap. For current disjoint pool definitions,
                    # it's less critical but good for robustness.
                    if demo not in selected_demos: 
                        selected_demos.append(demo)
                else:
                    break # Reached num_examples
            if len(selected_demos) >= num_examples:
                break # Reached num_examples
        
        return selected_demos

# --- Example Usage (Test Block) ---
if __name__ == '__main__':
    print("--- Testing Sampler ---")

    # Create an in-memory list of DemoData objects for testing
    # This replaces the need for mock CSV parsing within this test block.
    # The actual CSV parsing would happen in the client code (e.g., main.py)
    # using functions from your csv_input_loader.py.
    
    in_memory_demo_data_list: List[DemoData] = [
        DemoData(post_id="p1", item_category="Electronics", category="Gadgets", item_name="E-Reader X1", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="My E-Reader", content="Content for E-Reader", like_count=150, hashtags=["ereader", "books"], item_weight="0.3kg", discount="10%"),
        DemoData(post_id="p2", item_category="Electronics", category="Audio", item_name="Noise Cancelling Headphones Y2", item_unit_price=199.50, item_unit_price_currency="USD", item_url="url_hp", site="SoundGood", warehouse_id="WH-USE", warehouse_location="US-East", region="US", title="Quiet Time", content="Great for music", like_count=200, hashtags=["audio", "headphones"], item_weight="0.4kg"),
        DemoData(post_id="p3", item_category="Fashion", category="Accessories", item_name="Silk Scarf Z3", item_unit_price=80.00, item_unit_price_currency="EUR", item_url="url_scarf", site="EuroStyle", warehouse_id="WH-EU-C", warehouse_location="EU-Central", region="EU", title="Elegant Scarf", content="Soft and stylish", like_count=120, hashtags=["fashion", "silk"], item_weight="0.1kg"),
        DemoData(post_id="p4", item_category="Electronics", category="Gadgets", item_name="Smart Thermostat T4", item_unit_price=99.00, item_unit_price_currency="USD", item_url="url_thermo", site="HomeSmart", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="Smart Home!", content="Easy to install", like_count=180, hashtags=["smarthome", "iot"], item_weight="0.5kg"),
        DemoData(post_id="p5", item_category="Books", category="Fiction", item_name="The Great Novel N5", item_unit_price=15.99, item_unit_price_currency="CAD", item_url="url_novel", site="ReadMore", warehouse_id="WH-CA-E", warehouse_location="CA-East", region="CA", title="A Good Read", content="Page turner", like_count=90, hashtags=["fiction", "reading"], item_weight="0.6kg", discount="5%"),
        DemoData(post_id="p6", item_category="Electronics", region="CA", item_name="Tablet Pro", category="Computers", item_unit_price=499.00, item_unit_price_currency="CAD", item_url="url_tab", site="CanTech", warehouse_id="WH-CA-W", warehouse_location="CA-West", title="My New Tablet", content="Fast and light", like_count=250, hashtags=["tablet", "productivity"])
    ]

    try:
        sampler_instance = Sampler(all_demo_data=in_memory_demo_data_list)
        print(f"Sampler instance created. Total demos loaded: {len(sampler_instance._all_demos)}")

        print("\n--- Test Case 1: Match Region & Category (US, Electronics) ---")
        test_input_1 = InputData(item_category="Electronics", region="US", item_name="Test Item 1 SSD", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_1 = sampler_instance.retrieve_demos(test_input_1, num_examples=3)
        print(f"Retrieved {len(demos_1)} demos:")
        for d in demos_1:
            assert d.region == "US" # Should all be US
            # First few should ideally be Electronics if available
            print(f"  - {d.post_id}: {d.item_name} (Region: {d.region}, ItemCat: {d.item_category})")
        assert any(d.item_category == "Electronics" for d in demos_1) or len(demos_1) == 0


        print("\n--- Test Case 2: Match Region Only (US, NonExistentItemCat) ---")
        test_input_2 = InputData(item_category="NonExistentCategory", region="US", item_name="Test Item 2 Drone", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_2 = sampler_instance.retrieve_demos(test_input_2, num_examples=3)
        print(f"Retrieved {len(demos_2)} demos:")
        for d in demos_2:
            assert d.region == "US" # Should all be US
            # Should not be NonExistentCategory, but could be any other category in US
            print(f"  - {d.post_id}: {d.item_name} (Region: {d.region}, ItemCat: {d.item_category})")

        print("\n--- Test Case 3: No Region Match (NonExistentRegion) ---")
        test_input_3 = InputData(item_category="Whatever", region="NonExistentRegion", item_name="Test Item 3 AlienTech", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_3 = sampler_instance.retrieve_demos(test_input_3, num_examples=3)
        print(f"Retrieved {len(demos_3)} demos:")
        for d in demos_3:
            # Can be from any region/category now
            print(f"  - {d.post_id}: {d.item_name} (Region: {d.region}, ItemCat: {d.item_category})")
            
        print("\n--- Test Case 4: Requesting more than available in a specific pool (EU, Fashion) ---")
        # In in_memory_demo_data_list, there's 1 "Fashion" in "EU"
        test_input_4 = InputData(item_category="Fashion", region="EU", item_name="Test Item 4 Bag", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_4 = sampler_instance.retrieve_demos(test_input_4, num_examples=5) # Request 5
        print(f"Retrieved {len(demos_4)} demos (expected to pull from other pools after exhausting EU/Fashion):")
        found_eu_fashion = 0
        for d in demos_4:
            if d.region == "EU" and d.item_category == "Fashion":
                found_eu_fashion +=1
            print(f"  - {d.post_id}: {d.item_name} (Region: {d.region}, ItemCat: {d.item_category})")
        assert found_eu_fashion <= 1 # Based on our sample data
        assert len(demos_4) <= 5 # Should not exceed requested or total available

        print("\n--- Test Case 5: Empty Request ---")
        demos_5 = sampler_instance.retrieve_demos(test_input_1, num_examples=0)
        print(f"Retrieved {len(demos_5)} demos for num_examples=0.")
        assert len(demos_5) == 0
        
        print("\n--- Test Case 6: Sampler with Empty Demo List (should raise error) ---")
        try:
            empty_sampler = Sampler(all_demo_data=[])
        except ValueError as e:
            print(f"Correctly caught error for empty demo list: {e}")

    except Exception as e:
        print(f"An error occurred during sampler testing: {e}")
        import traceback
        traceback.print_exc()