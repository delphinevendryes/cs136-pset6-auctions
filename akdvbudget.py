#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index
import math
import random

class Akdvbudget:
    """Balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget
        self.estimated_values = []
        self.spent = []
        self.p = 0
        self.q = 0

    def initial_bid(self, reserve):
        # print((self.id, self.value))

        return self.value / 2 # for now, might change


    def update_spent(self, history, t, reserve):

        def bid_sort(bids):
            s = sorted(range(len(bids)), key=lambda k: bids[k][1], reverse=True)
            return [bids[j] for j in s]

        prev_round = history.round(t-1)
        bids = prev_round.bids
        valid_bids = filter(lambda (a_id, b): b >= reserve, bids)
        valid_bids = bid_sort(valid_bids)
        bids = bid_sort(bids)

        num_agents = len(bids)
        num_slots = len(prev_round.clicks)
        n_alloc = min(len(valid_bids), num_slots)

        if t == 1:
            self.spent = [0 for _ in range(num_agents)]

        for k, b in enumerate(valid_bids):
            agent_id = b[0]
            if k < n_alloc:
                self.spent[agent_id] += max(bids[k + 1][1], reserve)



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
        num_slots = len(clicks)
        for _ in range(len(all_bids), num_slots):
            all_bids.append(0)
        all_bids = [max(x, reserve) for x in all_bids ]

        all_expected_utilities = [clicks[i] * (self.value - max(all_bids[i], reserve)) for i in range(len(all_bids))]

        return all_expected_utilities

    def participate(self, t, bid):
        def sigmoid(x):
            return 1.0/(1.0+math.exp(-x))

        self_spent = self.spent[self.id]
        others_spent = [self.spent[i] for i in range(len(self.spent)) if i != self.id]
        p = sigmoid((t-24)/48 + (- bid - self_spent + sum(others_spent) / len(others_spent))/100)
        #print(p)
        r = random.random()
        if r < p:
            return True

        else:
            #print('did not participate')
            return False

    def target_slot(self, t, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i =  argmax_index(self.expected_utils(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def bid(self, t, history, reserve):
        # update record of spendings given last round
        self.update_spent(history, t, reserve)


        # compute BB
        prev_round = history.round(t-1)
        (slot, min_bid, max_bid) = self.target_slot(t, history, reserve)
        if slot == 0:
            bid = self.value
        else:
            # Need:
            # 1. our value.
            # 2. number of clicks for pos j over j-1.
            # 3. payment at pos star in previous round
            other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)
            all_bids = sorted([x[1] for x in other_bids], reverse=True)
            all_bids.append(0)
            all_bids = [max(x, reserve) for x in all_bids]
            t_star = all_bids[slot]
            if self.value - t_star < 0:
                bid = self.value
            else:
                ratio = (1.0 * prev_round.clicks[slot]) / (1.0 * prev_round.clicks[slot - 1])
                bid = self.value - ratio * (self.value - t_star)
                assert (bid >= min_bid) & (bid <= max_bid)

        participate = self.participate(t, bid)
        if not participate:
            self.q += 1
            return 0

            # self.estimate_values(t, history, reserve)
        else:
            self.p += 1
            #print(self.p, self.q)
            return bid

    def estimate_values(self, t, history, reserve): # this is assuming other players play BB
        # the values are drawn in U[25, 175]
        prev_round = history.round(t-1)

        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)
        # check that bids are sorted by agent id
        if t == 1: # at second round, estimate with the mean 100, to refine
            self.estimated_values = [(other_bids[k][0], 100) for k in range(len(other_bids))]

        # assume the agents are playing balanced bidding
        else :
            prevprev_round = history.round(t - 2)
            clicks = prevprev_round.clicks
            for i in range(len(other_bids)):
                # assume agent i is playing balanced bids in round t-1
                id_i = other_bids[i][0]
                bid_i = other_bids[i][1]

                other_bids_i = filter(lambda (a_id, b): a_id != id_i, prevprev_round.bids)
                other_bids_i = sorted([x[1] for x in other_bids_i], reverse=True)

                num_slots = len(clicks)

                for _ in range(len(other_bids_i), num_slots):
                    other_bids_i.append(0)

                other_bids_i = [max(x, reserve) for x in other_bids_i]
                expected_utilities_i = [clicks[k] * (self.estimated_values[i][1] - max(other_bids_i[k], reserve)) for k in range(len(other_bids_i))]

                target_slot_i = argmax_index(expected_utilities_i)

                if target_slot_i == 0:
                    value_i = bid_i

                elif expected_utilities_i[target_slot_i] < 0:
                    value_i = bid_i
                else :
                    t_star_i = other_bids_i[target_slot_i]
                    value_i = (clicks[target_slot_i] * t_star_i - bid_i * clicks[target_slot_i - 1]) / \
                              (clicks[target_slot_i] - clicks[target_slot_i-1])

                if value_i < 25:
                     value_i = 25

                if value_i > 175:
                     value_i = 175

                if t == 2:
                    self.estimated_values[i] = (id_i, value_i)
                else:
                    self.estimated_values[i] = (id_i, (self.estimated_values[i][1] * (t-2) + value_i)/(t-1))

                self.estimated_values[i] = (id_i, value_i)
        #print('Guess from agent %d at round %d' )% (self.id, t)
        #print(self.estimated_values)


    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


