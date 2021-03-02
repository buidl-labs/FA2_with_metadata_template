# change token name to token_metadata
import smartpy as sp
FA2 = sp.import_script_from_url("https://raw.githubusercontent.com/buidl-labs/FA2_with_metadata_template/main/fa2_latest_mod.py")

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
        sp.if self.data.token_metadata.contains(params.token_id):
             pass
        sp.else:
             self.data.token_metadata[params.token_id] = self.token_meta_data.make(
                 amount = params.amount,
                 metadata = params.metadata)
        
    @sp.entry_point
    def transfer(self, params):
        sp.verify( ~self.is_paused() )
        sp.set_type(params, self.batch_transfer.get_type())
        sp.for transfer in params:
          current_from = transfer.from_
          sp.for tx in transfer.txs:
                #sp.verify(tx.amount > 0, message = "TRANSFER_OF_ZERO")
                if self.config.single_asset:
                    sp.verify(tx.token_id == 0, "single-asset: token-id <> 0")
                if self.config.support_operator:
                          sp.verify(
                              (self.is_administrator(sp.sender)) |
                              (current_from == sp.sender) |
                              self.operator_set.is_member(self.data.operators,
                                                          current_from,
                                                          sp.sender,
                                                          tx.token_id),
                              message = self.error_message.not_operator())
                else:
                          sp.verify(
                              (self.is_administrator(sp.sender)) |
                              (current_from == sp.sender),
                              message = self.error_message.not_owner())
                sp.verify(self.data.token_metadata.contains(tx.token_id),
                          message = self.error_message.token_undefined())
                # If amount is 0 we do nothing now:
                sp.if (tx.amount > 0):
                    from_user = self.ledger_key.make(current_from, tx.token_id)
                    sp.verify(
                        (self.data.ledger[from_user].balance >= tx.amount),
                        message = self.error_message.insufficient_balance())
                    to_user = self.ledger_key.make(tx.to_, tx.token_id)
                    self.data.ledger[from_user].balance = sp.as_nat(
                        self.data.ledger[from_user].balance - tx.amount)
                    sp.if self.data.ledger.contains(to_user):
                        self.data.ledger[to_user].balance += tx.amount
                    sp.else:
                         self.data.ledger[to_user] = FA2.Ledger_value.make(tx.amount)
                sp.else:
                    pass
                
                # Remove bot from sale if true
                user = self.ledger_key.make(current_from, tx.token_id)
        
                #Make sure that the caller is the owner of NFT token id else throw error 
                sp.if self.data.ledger.contains(user):
                    # Remove NFT token id from offers list
                    sp.if self.data.offer.contains(tx.token_id):
                        del self.data.offer[tx.token_id]
        


if "templates" not in __name__:
    @sp.add_test(name = "NFT Cryptobot collectables")
    def test():
        scenario = sp.test_scenario()
        scenario.h1("NFT Cryptobot collectables")

        scenario.table_of_contents()

        scenario.h2("Accounts")
        admin = sp.address("tz1iLVzBpCNTGz6tCBK2KHaQ8o44mmhLTBio")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")

        scenario.show([alice, bob])

        scenario.h2("Contract")

        # TODO: add latest contract metadata json 
        
        c1 = Cryptobot( config = FA2.FA2_config(non_fungible = True, assume_consecutive_token_ids = False, store_total_supply = False),
                      metadata=sp.metadata_of_url("ipfs://QmeGcWmfPnnnFtfzPy2CyCww14iUvtgRgYRXF34Lzn6oQU"),
                      admin = admin
        )
        scenario += c1
        

        scenario += c1.mint(address = alice.address, 
                            amount = 1,
                            token_id = 1,
                            metadata = {'uri': "insert bot hash here", "symbol":"CB"}).run(sender = alice)
        
        scenario += c1.mint(address = alice.address, 
                            amount = 1,
                            token_id = 5,
                            metadata = {'uri': "insert bot hash here",
                            "symbol": "CB" }).run(sender = alice)
        
        
        scenario += c1.offer_bot_for_sale(token_id = 5, sale_price = sp.mutez(1000)).run(sender = alice)
    
        # scenario += c1.purchase_bot_at_sale_price(token_id = 5).run(sender = bob, amount = sp.mutez(1000))
        
        # scenario += c1.bot_no_longer_for_sale(token_id = 5).run(sender = alice)
        scenario += c1.transfer(
                [
                    c1.batch_transfer.item(from_ = alice.address,
                                        txs = [
                                            sp.record(to_ = bob.address,
                                                      amount = 1,
                                                      token_id = 1)])
                ]).run(sender = alice)
