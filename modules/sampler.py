from typing import List

from modules.models import InputData

class Sampler:
    """
    A sampler for retrieving demo examples based on input data criteria.
    Demos are prioritized by like_count within filtered buckets.
    The demo data list is provided at instantiation.
    """
    _all_demos: List[InputData]

    def __init__(self, all_demo_data: List[InputData]):
        """
        Initializes the Sampler with a pre-loaded list of InputData objects.

        Args:
            all_demo_data: A list of InputData objects.
        
        Raises:
            ValueError: If the provided all_demo_data list is empty or None.
        """
        if not all_demo_data:
            raise ValueError("The provided 'all_demo_data' list cannot be None or empty.")
        
        self._all_demos = list(all_demo_data) 
        print(f"Sampler initialized with {len(self._all_demos)} demo items.")

    def retrieve_demos(self, input_data: InputData, num_examples: int) -> List[InputData]:
        """
        Retrieves a list of demo examples based on hierarchical filtering,
        prioritizing by highest 'like_count' in each tier.

        The selection priority is:
        1. Highest 'like_count' from demos matching both input_data.region and input_data.item_category.
        2. Highest 'like_count' from demos matching input_data.region only (different item_category).
        3. Highest 'like_count' from demos matching input_data.item_category only (different region).
        4. Highest 'like_count' from remaining demos (not matching input_data.region nor input_data.item_category).

        Args:
            input_data: The InputData object for the current item being processed.
            num_examples: The desired number of demo examples to retrieve.

        Returns:
            A list of InputData objects, up to num_examples.
        """
        if num_examples <= 0:
            return []
        if not self._all_demos:
            return []

        selected_demos: List[InputData] = []
        
        # Tier 1: Match region AND item_category (Pool B)
        pool_b = [
            demo for demo in self._all_demos
            if demo.region == input_data.region and demo.item_category == input_data.item_category
        ]
        pool_b.sort(key=lambda demo: demo.like_count, reverse=True)

        # Tier 2: Match region ONLY (different item_category) (Pool A')
        pool_a_prime = [
            demo for demo in self._all_demos
            if demo.region == input_data.region and demo.item_category != input_data.item_category
        ]
        pool_a_prime.sort(key=lambda demo: demo.like_count, reverse=True)

        # Tier 3: Match item_category ONLY (different region) (Pool D') - NEW TIER
        pool_d_prime = [
            demo for demo in self._all_demos
            if demo.item_category == input_data.item_category and demo.region != input_data.region
        ]
        pool_d_prime.sort(key=lambda demo: demo.like_count, reverse=True)
        
        # Tier 4: No match on region AND no match on item_category (Pool E')
        pool_e_prime = [
            demo for demo in self._all_demos
            if demo.region != input_data.region and demo.item_category != input_data.item_category
        ]
        pool_e_prime.sort(key=lambda demo: demo.like_count, reverse=True)
        
        # Fill selected_demos from sorted pools in order of priority
        # The pools are defined to be disjoint and cover all possibilities.
        for demo_pool in [pool_b, pool_a_prime, pool_d_prime, pool_e_prime]:
            for demo in demo_pool:
                if len(selected_demos) < num_examples:
                    # Add if not already selected (safeguard, though current pools are disjoint)
                    if demo not in selected_demos: 
                        selected_demos.append(demo)
                else:
                    break # Reached num_examples
            if len(selected_demos) >= num_examples:
                break # Reached num_examples
        
        # print(selected_demos)
        return selected_demos

# --- Example Usage (Test Block) ---
if __name__ == '__main__':
    print("--- Testing Sampler (Prioritizing by Like Count with 4 Tiers) ---")
    
    # More diverse data for testing all tiers
    in_memory_demo_data_list: List[InputData] = [
        # US, Electronics
        InputData(post_id="p1", item_category="Electronics", category="Gadgets", item_name="E-Reader X1 (US)", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er_us", site="TechFindsUS", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="My US E-Reader", content="Content US", like_count=150),
        InputData(post_id="p2", item_category="Electronics", category="Audio", item_name="Headphones Y2 (US)", item_unit_price=199.50, item_unit_price_currency="USD", item_url="url_hp_us", site="SoundGoodUS", warehouse_id="WH-USE", warehouse_location="US-East", region="US", title="US Quiet Time", content="Music US", like_count=200),
        InputData(post_id="p4", item_category="Electronics", category="Gadgets", item_name="Thermostat T4 (US)", item_unit_price=99.00, item_unit_price_currency="USD", item_url="url_thermo_us", site="HomeSmartUS", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="US Smart Home", content="Install US", like_count=180),
        # US, Other Category
        InputData(post_id="p7", item_category="Home Goods", category="Kitchen", item_name="Coffee Maker (US)", item_unit_price=90.00, item_unit_price_currency="USD", item_url="url_coffee_us", site="KitchenUS", warehouse_id="WH-USC", warehouse_location="US-Central", region="US", title="US Coffee", content="Best brew US", like_count=170),
        # EU, Fashion
        InputData(post_id="p3", item_category="Fashion", category="Accessories", item_name="Silk Scarf Z3 (EU)", item_unit_price=80.00, item_unit_price_currency="EUR", item_url="url_scarf_eu", site="EuroStyle", warehouse_id="WH-EU-C", warehouse_location="EU-Central", region="EU", title="EU Elegant Scarf", content="Soft EU", like_count=120),
        # EU, Electronics
        InputData(post_id="p8", item_category="Electronics", category="Gadgets", item_name="E-Reader X1 (EU)", item_unit_price=139.99, item_unit_price_currency="EUR", item_url="url_er_eu", site="TechFindsEU", warehouse_id="WH-EUE", warehouse_location="EU-East", region="EU", title="My EU E-Reader", content="Content EU", like_count=160), # EU version of E-Reader
        # CA, Books
        InputData(post_id="p5", item_category="Books", category="Fiction", item_name="The Great Novel N5 (CA)", item_unit_price=15.99, item_unit_price_currency="CAD", item_url="url_novel_ca", site="ReadMoreCA", warehouse_id="WH-CA-E", warehouse_location="CA-East", region="CA", title="CA Good Read", content="Page turner CA", like_count=90),
        # CA, Electronics
        InputData(post_id="p6", item_category="Electronics", category="Computers", item_name="Tablet Pro (CA)", item_unit_price=499.00, item_unit_price_currency="CAD", item_url="url_tab_ca", site="CanTech", warehouse_id="WH-CA-W", warehouse_location="CA-West", region="CA", title="CA New Tablet", content="Fast CA", like_count=250),
        # AU, Other Category (neither Electronics nor Books, for full fallback)
        InputData(post_id="p9", item_category="Sports", category="Outdoor", item_name="Tent Z1 (AU)", item_unit_price=299.00, item_unit_price_currency="AUD", item_url="url_tent_au", site="AusOutdoor", warehouse_id="WH-AU-S", warehouse_location="AU-Sydney", region="AU", title="AU Camping", content="Great tent AU", like_count=100),
    ]

    try:
        sampler_instance = Sampler(all_demo_data=in_memory_demo_data_list)
        print(f"Sampler instance created. Total demos loaded: {len(sampler_instance._all_demos)}")

        print("\n--- Test Case 1: Match Region & Category (US, Electronics), num_examples=2 ---")
        # Pool B (US, Electronics): p2 (200), p4 (180), p1 (150)
        test_input_1 = InputData(item_name="Test 1", item_category="Electronics", region="US", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_1 = sampler_instance.retrieve_demos(test_input_1, num_examples=2)
        print(f"Retrieved {len(demos_1)} demos:")
        like_counts_1 = [d.like_count for d in demos_1]
        for d in demos_1: print(f"  - {d.post_id}: {d.item_name} (Likes: {d.like_count}, R:{d.region}, IC:{d.item_category})")
        assert like_counts_1 == [200, 180]

        print("\n--- Test Case 2: Match Region Only (US, Books), num_examples=2 ---")
        # Pool B (US, Books): Empty
        # Pool A' (US, not Books = US/Electronics + US/Home Goods): p2(200), p4(180), p7(170), p1(150)
        test_input_2 = InputData(item_name="Test 2", item_category="Books", region="US", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_2 = sampler_instance.retrieve_demos(test_input_2, num_examples=2)
        print(f"Retrieved {len(demos_2)} demos:")
        like_counts_2 = [d.like_count for d in demos_2]
        for d in demos_2: print(f"  - {d.post_id}: {d.item_name} (Likes: {d.like_count}, R:{d.region}, IC:{d.item_category})")
        assert like_counts_2 == [200, 180] # From US/Electronics & US/Home Goods (p2,p4 from US/Elec)

        print("\n--- Test Case 3: Match Item Category Only (EU, Electronics), num_examples=3 ---")
        # Pool B (EU, Electronics): p8 (160)
        # Pool A' (EU, not Electronics = EU/Fashion): p3 (120)
        # Pool D' (not EU, Electronics = CA/Electronics + US/Electronics): p6(250), p2(200), p4(180), p1(150)
        # Expected pick order: p8(160), p3(120), then p6(250)
        test_input_3 = InputData(item_name="Test 3", item_category="Electronics", region="EU", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD") # Input region is EU
        demos_3 = sampler_instance.retrieve_demos(test_input_3, num_examples=3)
        print(f"Retrieved {len(demos_3)} demos:")
        ids_3 = [d.post_id for d in demos_3]
        like_counts_3 = [d.like_count for d in demos_3]
        for d in demos_3: print(f"  - {d.post_id}: {d.item_name} (Likes: {d.like_count}, R:{d.region}, IC:{d.item_category})")
        # This test actually tests the new Pool D' logic implicitly if Pool A' and B for input EU/Electronics aren't enough.
        # Re-evaluating for input (item_category="Electronics", region="EU"):
        # Pool B (EU, Electronics): p8 (160)
        # Pool A' (EU, !Electronics = EU/Fashion): p3 (120)
        # Pool D' (!EU, Electronics): p6 (250, CA), p2 (200, US), p4 (180, US), p1 (150, US)
        # Expected order for 3 examples: p8, p6, p2 (because after exhausting EU/Elec (p8), and EU/!Elec (p3), it should go to !EU/Elec and pick p6 then p2)
        # Wait, the prompt asks for input (item_category="Electronics", region="EU")
        # Pick 1: p8 from Pool B (EU, Electronics) - 160 likes
        # Remaining to pick: 2
        # Pick 2: p3 from Pool A' (EU, Fashion) - 120 likes
        # Remaining to pick: 1
        # Pick 3: p6 from Pool D' (CA, Electronics) - 250 likes. This order is not right.
        # The iteration is: pool_b, pool_a_prime, pool_d_prime, pool_e_prime.
        # So for test_input_3 (item_category="Electronics", region="EU"):
        # From pool_b (EU, Electronics): p8 (160). selected_demos = [p8]
        # From pool_a_prime (EU, !Electronics = EU/Fashion): p3 (120). selected_demos = [p8, p3]
        # From pool_d_prime (!EU, Electronics): p6 (250), p2 (200), p4 (180), p1 (150). Next pick is p6. selected_demos = [p8, p3, p6]
        assert ids_3 == ["p8", "p3", "p6"]
        assert like_counts_3 == [160, 120, 250]


        print("\n--- Test Case 4: No Region or Category Match (UK, Garden), num_examples=2 ---")
        # Pool B (UK, Garden): Empty
        # Pool A' (UK, !Garden): Empty
        # Pool D' (!UK, Garden): Empty
        # Pool E' (!UK, !Garden - basically all items, sorted by likes): p6(250), p2(200), p4(180), p7(170), p8(160), p1(150), p3(120), p5(90), p9(100)
        # Should be sorted: p6(250), p2(200), p4(180), p7(170), p8(160), p1(150), p3(120), p9(100), p5(90)
        test_input_4 = InputData(item_name="Test 4", item_category="Garden", region="UK", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er", site="TechFinds", warehouse_id="WH-USW", warehouse_location="US-West", url_extracted_text="SSSD")
        demos_4 = sampler_instance.retrieve_demos(test_input_4, num_examples=2)
        print(f"Retrieved {len(demos_4)} demos:")
        like_counts_4 = [d.like_count for d in demos_4]
        for d in demos_4: print(f"  - {d.post_id}: {d.item_name} (Likes: {d.like_count}, R:{d.region}, IC:{d.item_category})")
        assert like_counts_4 == [250, 200] # p6, p2

    except Exception as e:
        print(f"An error occurred during sampler testing: {e}")
        import traceback
        traceback.print_exc()