import logging

from pokete.classes.daily_quests import QuestEvent
from pokete.classes.daily_quests.quest_tracker import quest_tracker


class Bank:
    __money: int

    def __init__(self, money:int):
        self.__money = money

    def add_money(self, money:int):
        """Adds money
        ARGS:
            money: Amount of money being added"""
        old_money = self.__money
        self.set_money(self.__money + money)
        # Emit quest event for positive money gains
        if money > 0:
            quest_tracker.emit(QuestEvent.coins_collected(money))

    def get_money(self):
        """Getter for __money
        RETURNS:
            The current money"""
        return self.__money

    def set_money(self, money:int):
        """Sets the money to a certain value
        ARGS:
            money: New value"""
        assert money >= 0, "Money has to be positive."
        logging.info("[Figure] Money set to $%d from $%d",
                     money, self.__money)
        self.__money = money
