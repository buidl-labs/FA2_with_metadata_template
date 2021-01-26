import smartpy as sp
FA2 = sp.import_script_from_url("https://raw.githubusercontent.com/buidl-labs/FA2_with_metadata_template/main/fa2-smartpy.py")

class Offer:
    """
    type offer = {
        key = nat : {
            is_for_sale = boolean,
            seller = address,
            sale_value = mutez
        }
    }
    """
    
    def get_value_type():
        return sp.TRecord(
            is_for_sale = sp.TBool,
            seller = sp.TAddress,
            sale_value = sp.TMutez
        )
    
    def get_key_type():
        """ Cryptobot Token ID """
        return sp.TNat

class Cryptobot(FA2.FA2):
    def __init__(self, config, metadata, admin):
        FA2.FA2_core.__init__(self, config, metadata,
            paused = False, administrator = admin,
            offer = sp.big_map(tkey = Offer.get_key_type(), tvalue = Offer.get_value_type()),
            current_supply = sp.nat(0),
            initial_hodlers = sp.big_map(tkey = sp.TAddress, tvalue = sp.TNat))
            
    @sp.entry_point
    def offer_bot_for_sale(self, params):
        
        sp.verify(~ self.data.paused)
        
        sp.set_type(params.token_id, sp.TNat)
        sp.set_type(params.sale_price, sp.TMutez)
        
        # Make sure that the NFT token id is already present
        sp.verify(self.token_id_set.contains(self.data.all_tokens, params.token_id), "TOKEN ID NOT FOUND")
        
        # Make sure that sale_value is more than zero mutez
        sp.verify(params.sale_price > sp.mutez(0), "MIN VALUE SHOULD BE MORE THAN ZERO")
        user = self.ledger_key.make(sp.sender, params.token_id)
        
        #Make sure that the caller is the owner of NFT token id else throw error 
        sp.if self.data.ledger.contains(user):
            # Make NFT with token id open for offers
            self.data.offer[params.token_id] = sp.record(is_for_sale = True, seller = sp.sender, sale_value = params.sale_price)
        sp.else:
            sp.failwith("NOT OWNER OF NFT TOKEN ID")
    
    @sp.entry_point
    def bot_no_longer_for_sale(self, params):

        sp.verify(~ self.data.paused)
        
        sp.set_type(params.token_id, sp.TNat)
        
        # Make sure that the NFT token id is already present
        sp.verify(self.token_id_set.contains(self.data.all_tokens, params.token_id), "TOKEN ID NOT FOUND")
        
        # Make sure that token id is available for withdrwal from sale
        sp.verify(self.data.offer.contains(params.token_id), "NFT TOKEN ID NOT AVAILABLE FOR WITHDRWAL")
        
        user = self.ledger_key.make(sp.sender, params.token_id)
        
        #Make sure that the caller is the owner of NFT token id else throw error 
        sp.if self.data.ledger.contains(user):
            # Remove NFT token id from offers list
            del self.data.offer[params.token_id]
        sp.else:
            sp.failwith("NOT OWNER OF NFT TOKEN ID")
            
    @sp.entry_point
    def purchase_bot_at_sale_price(self, params):
        sp.verify(~ self.data.paused)
        
        sp.set_type(params.token_id, sp.TNat)
        
        # Make sure that the NFT token id is already present in the ledger
        sp.verify(self.token_id_set.contains(self.data.all_tokens, params.token_id), "TOKEN ID NOT FOUND")
        
        # Make sure that NFT token id is listed for sale
        sp.verify(self.data.offer.contains(params.token_id) == True, "NFT TOKEN ID NOT AVAILABLE FOR SALE")
        
        # Make sure NFT token id is up for sale
        sp.verify(self.data.offer[params.token_id].is_for_sale == True, "NFT TOKEN ID IS NOT UP FOR SALE")
        

        # Get owner of the token_id which is for sale
        seller = self.data.offer[params.token_id].seller
        
        # Make sure seller is owner of the token id
        user = self.ledger_key.make(seller, params.token_id)
        sp.verify(self.data.ledger.contains(user) == True, "NOT OWNER OF NFT TOKEN ID")
        
        # Make sure that sale value is equivalent to sp.amount
        sp.verify(self.data.offer[params.token_id].sale_value == sp.amount, "INCORRECT AMOUNT")
        
        # transfer ownership to the highest bidder account
        from_user = self.ledger_key.make(seller, params.token_id)
        to_user = self.ledger_key.make(sp.sender, params.token_id)
        
        self.data.ledger[from_user].balance = sp.as_nat(
            self.data.ledger[from_user].balance - 1)
            
        sp.if self.data.ledger.contains(to_user):
            self.data.ledger[to_user].balance += 1
        sp.else:
             self.data.ledger[to_user] = FA2.Ledger_value.make(1)
        
        # Transfer xtz to the seller
        sp.send(self.data.offer[params.token_id].seller, sp.amount)
        
        # Remove NFT token id from offer for sale
        del self.data.offer[params.token_id]
            
    @sp.entry_point
    def mint(self, params):
        
        sp.verify(~ self.data.paused)
        
        self.data.current_supply = sp.len(self.data.all_tokens)
        
        # Limit total supply to 10,000 3D Cryptobots
        sp.verify(self.data.current_supply < 10000, "3D Cryptobot NFT creation limit exceeded")
        
        # Don't let one tezos address to mint more than 5 cryptobots
        sp.if self.data.initial_hodlers.contains(sp.sender):
            sp.if self.data.initial_hodlers[sp.sender] < 5:
                self.data.initial_hodlers[sp.sender] = self.data.initial_hodlers[sp.sender] + 1
            sp.else:
                sp.failwith("Cryptobot minting limit reached")
        sp.else:
            self.data.initial_hodlers[sp.sender] = 1
        
        if self.config.single_asset:
            sp.verify(params.token_id == 0, "single-asset: token-id <> 0")
        if self.config.non_fungible:
            sp.verify(params.amount == 1, "NFT-asset: amount <> 1")
            sp.verify(~ self.token_id_set.contains(self.data.all_tokens,
                                                   params.token_id),
                      "NFT-asset: cannot mint twice same token")
        user = self.ledger_key.make(params.address, params.token_id)
        self.token_id_set.add(self.data.all_tokens, params.token_id)
        sp.if self.data.ledger.contains(user):
            self.data.ledger[user].balance += params.amount
        sp.else:
            self.data.ledger[user] = FA2.Ledger_value.make(params.amount)
        sp.if self.data.tokens.contains(params.token_id):
             pass
        sp.else:
             self.data.tokens[params.token_id] = self.token_meta_data.make(
                 amount = params.amount,
                 metadata = params.metadata)


if "templates" not in __name__:
    @sp.add_test(name = "NFT Cryptobot collectables")
    def test():
        scenario = sp.test_scenario()
        scenario.h1("NFT Cryptobot collectables")

        scenario.table_of_contents()

        scenario.h2("Accounts")
        admin = sp.address("tz1XP2AUZAaCbi1PCNQ7pEdMS1EEjL4p4YPY")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")

        scenario.show([alice, bob])

        scenario.h2("Contract")

        # TODO: add latest contract metadata json 
        
        c1 = Cryptobot( config = FA2.FA2_config(non_fungible = True, assume_consecutive_token_ids = False),
                      metadata=sp.bytes_of_string("ipfs://QmRgkniro5VxsibVx5MgwcGnXRMna4g3zeLUwHEmS6r5kL"),
                      admin = admin
        )
        scenario += c1
        tok0_md = Cryptobot.make_metadata(
            symbol = "CB",
            name = "3D Cryptobots",
            decimals = 0,
        )
        scenario += c1.mint(address = alice.address, 
                            amount = 1,
                            token_id = 1,
                            metadata = {'uri': sp.bytes_of_string("<insert bot hash here>"), "symbol": sp.bytes_of_string("CB")}).run(sender = alice)
        
        scenario += c1.mint(address = alice.address, 
                            amount = 1,
                            token_id = 5,
                            metadata = {'uri': sp.bytes_of_string("<insert bot hash here>"),
                            "symbol": sp.bytes_of_string("CB")}).run(sender = alice)
        
        
        scenario += c1.offer_bot_for_sale(token_id = 5, sale_price = sp.mutez(1000)).run(sender = alice)
    
        # scenario += c1.purchase_bot_at_sale_price(token_id = 5).run(sender = bob, amount = sp.mutez(1000))
        
        scenario += c1.bot_no_longer_for_sale(token_id = 5).run(sender = alice)
