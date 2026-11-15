# Normalization: my study notes

## Why normalize at all?

A badly designed table stores the same fact in many rows. That causes three kinds of anomalies. An update anomaly happens when a fact changes and you have to edit many rows; miss one and the data contradicts itself. An insertion anomaly happens when you cannot record a fact until some unrelated fact exists, like not being able to add a new menu item until someone orders it. A deletion anomaly happens when deleting one row accidentally destroys the only copy of another fact, like losing a customer's city when their only order is deleted.

Normalization fixes this by splitting a table into smaller tables so that each fact is stored exactly once. The split must be lossless: joining the smaller tables back together must give exactly the original rows, no more and no fewer.

## Functional dependencies and keys

A functional dependency X -> Y means that any two rows that agree on X must also agree on Y. For example, customer_id -> customer_name: one customer id can never map to two different names. The dependency is about the meaning of the data, not about whatever rows happen to be in the table today.

A superkey is any set of attributes that determines every other attribute. A candidate key is a minimal superkey: remove any attribute and it stops being a key. The primary key is the candidate key we choose to use. An attribute is prime if it belongs to at least one candidate key, and non-prime otherwise.

## The normal forms in one line each

1NF: every cell holds a single atomic value, there are no repeating groups or lists inside a cell, and rows can be uniquely identified.

2NF: 1NF, and no non-prime attribute depends on only part of a candidate key. This can only be violated when a key has more than one attribute.

3NF: 2NF, and no non-prime attribute depends on another non-prime attribute. Formally: for every non-trivial dependency X -> A, either X is a superkey or A is prime.

BCNF: for every non-trivial dependency X -> A, X is a superkey. No exceptions for prime attributes, which makes BCNF stricter than 3NF.

## Worked example: a food delivery app

Start with one wide table, one row per item in an order:

ORDER_LINE(order_id, item_id, order_date, customer_id, customer_name, customer_city, city_delivery_fee, item_name, unit_price, quantity)

The dependencies are: order_id -> order_date, customer_id. customer_id -> customer_name, customer_city. customer_city -> city_delivery_fee. item_id -> item_name, unit_price. (order_id, item_id) -> quantity. The key is (order_id, item_id).

Problems: order_date depends only on order_id and item_name depends only on item_id, so those are partial dependencies and the table is not in 2NF. city_delivery_fee depends on customer_city, which is not a key, so there is also a transitive chain order_id -> customer_id -> customer_city -> city_delivery_fee.

Step to 2NF: move everything that depends on only part of the key into its own table. ORDERS(order_id, order_date, customer_id, customer_name, customer_city, city_delivery_fee). ITEM(item_id, item_name, unit_price). ORDER_LINE(order_id, item_id, quantity), where order_id and item_id are both foreign keys and together form the key.

Step to 3NF: ORDERS still has non-key attributes depending on other non-key attributes. Split them out: ORDERS(order_id, order_date, customer_id). CUSTOMER(customer_id, customer_name, customer_city). CITY(city, delivery_fee). Now changing a city's delivery fee is a one-row update, and a customer's city survives even if all their orders are deleted.

A real-world catch: if prices change over time, the price a customer actually paid is a different fact from the item's current price. It belongs in ORDER_LINE as price_paid. Storing it there is not a normalization mistake, because it is not determined by item_id alone.

## When 3NF is not enough: BCNF

Example: a sports club where each coach teaches exactly one sport, and each member has one coach per sport. Table: TRAINING(member_id, sport, coach). Dependencies: (member_id, sport) -> coach, and coach -> sport. Candidate keys: (member_id, sport) and (member_id, coach).

This is in 3NF, because in coach -> sport the attribute sport is prime. It is not in BCNF, because coach is not a superkey. The anomaly: if a coach switches sports, many rows must change. Splitting into COACH(coach, sport) and MEMBER_COACH(member_id, coach) reaches BCNF, but now the rule "one coach per sport per member" can no longer be enforced inside a single table. BCNF decompositions are always lossless but do not always preserve every dependency; 3NF decompositions can always do both.

## Trade-offs

More tables means more joins, which can slow down read-heavy queries. Analytics systems often denormalize on purpose, copying data to avoid joins, and accept the extra work of keeping copies in sync. The usual practice is to design in 3NF or BCNF first, then denormalize only where you have measured a real performance problem.

## Self-check

Can I list the functional dependencies of a table before naming its normal form? Can I find every candidate key, not just the obvious one? For each dependency, is the left side a superkey? If not, is the right side prime (3NF) or does that already fail BCNF? After splitting, does joining the tables back give exactly the original data?
