#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index
import math

class Akdvbb:
    """Balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget

    def initial_bid(self, reserve):
        return self.value / 2


    def slot_info(self, t, history, reserve):
        """Compute the following for each slot, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns list of tuples [(slot_id, min_bid, max_bid)], where
        min_bid is the bid needed to tie the other-agent bid for that slot
        in the last round.  If slot_id = 0, max_bid is 2* min_bid.
        Otherwise, it's the next highest min_bid (so bidding between min_bid
        and max_bid would result in ending up in that slot)
        """
        prev_round = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)

        clicks = prev_round.clicks
        def compute(s):
            (min, max) = GSP.bid_range_for_slot(s, clicks, reserve, other_bids)
            if max == None:
                max = 2 * min
            return (s, min, max)
            
        info = map(compute, range(len(clicks)))
#        sys.stdout.write("slot info: %s\n" % info)
        return info


    def top_position(self, t):
        return round(30 * math.sin(math.pi * t / 24) + 50)
    
    def clicks_all(self, t, n):
        res = []
        temp = self.top_position(t)
        res.append(temp)
        for _ in range(0, n):
            temp *= 0.75
            res.append(temp)
        return(res)
    
    def expected_utils(self, t, history, reserve):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of utilities per slot.
        """
        # TODO: Fill this in
        prev_round = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)
        clicks = prev_round.clicks
        all_bids = sorted([x[1] for x in other_bids], reverse=True)
        all_expected_utilities = [clicks[i] * (self.value - all_bids[i]) for i in range(len(all_bids))]
        return all_expected_utilities

    def target_slot(self, t, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i = argmax_index(self.expected_utils(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def bid(self, t, history, reserve):
        # The Balanced bidding strategy (BB) is the strategy for a player j that, given
        # bids b_{-j},
        # - targets the slot s*_j which maximizes his utility, that is,
        # s*_j = argmax_s {clicks_s (v_j - t_s(j))}.
        # - chooses his bid b' for the next round so as to
        # satisfy the following equation:
        # clicks_{s*_j} (v_j - t_{s*_j}(j)) = clicks_{s*_j-1}(v_j - b')
        # (p_x is the price/click in slot x)
        # If s*_j is the top slot, bid the value v_j

        prev_round = history.round(t-1)
        (slot, min_bid, max_bid) = self.target_slot(t, history, reserve)
        # TODO: Fill this in.
        if slot == 0:
            bid = self.value

        else:
            # Need:
            # 1. our value.
            # 2. number of clicks for pos j over j-1.
            # 3. payment at pos star in previous round
            other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)
            all_bids = sorted([x[1] for x in other_bids], reverse=True)
            t_star = all_bids[slot]
            if self.value - t_star < 0:
                bid = self.value
            else:
                ratio = (1.0 * prev_round.clicks[slot]) / (1.0 * prev_round.clicks[slot - 1])
                bid = self.value - ratio * (self.value - t_star)
                assert (bid >= min_bid) & (bid <= max_bid)
        return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


