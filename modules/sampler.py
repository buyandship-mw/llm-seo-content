from typing import List

from modules.models import PostData

class Sampler:
    """
    A sampler for retrieving demo examples based on input data criteria.
    Demos are prioritized by like_count within filtered buckets.
    The demo data list is provided at instantiation.
    """
    _all_demos: List[PostData]

    def __init__(self, all_demo_data: List[PostData]):
        """
        Initializes the Sampler with a pre-loaded list of ``PostData`` objects.

        Args:
            all_demo_data: A list of ``PostData`` objects.
        
        Raises:
            ValueError: If the provided all_demo_data list is empty or None.
        """
        if not all_demo_data:
            raise ValueError("The provided 'all_demo_data' list cannot be None or empty.")
        
        self._all_demos = list(all_demo_data) 
        print(f"Sampler initialized with {len(self._all_demos)} demo items.")

    def retrieve_demos(self, input_data: PostData, num_examples: int) -> List[PostData]:
        """
        Retrieves a list of demo examples based on hierarchical filtering,
        prioritizing by highest 'like_count' in each tier.

        The selection priority is:
        1. Highest 'like_count' from demos matching both input_data.region and input_data.item_category.
        2. Highest 'like_count' from demos matching input_data.region only (different item_category).
        3. Highest 'like_count' from demos matching input_data.item_category only (different region).
        4. Highest 'like_count' from remaining demos (not matching input_data.region nor input_data.item_category).

        Args:
            input_data: The ``PostData`` object for the current item being processed.
            num_examples: The desired number of demo examples to retrieve.

        Returns:
            A list of ``PostData`` objects, up to num_examples.
        """
        if num_examples <= 0:
            return []
        if not self._all_demos:
            return []

        selected_demos: List[PostData] = []
        
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


# --- Example Usage ---
if __name__ == '__main__':
    print('Sampler module executed directly. No demo implemented.')
