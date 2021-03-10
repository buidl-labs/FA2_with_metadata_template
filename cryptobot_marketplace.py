import smartpy as sp

FA2 = sp.import_script_from_url("https://smartpy.io/templates/FA2.py")

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
        list_of_views = [
            self.get_balance
            , self.token_metadata
            , self.does_token_exist
            , self.count_tokens
            , self.all_tokens
            , self.is_operator
        ]
        metadata_base = {
          "name": "3D Cryptobot"
          , "version": "1.0"
          , "description" :"Users created NFT 3D Cryptobots."
          , "interfaces": ["TZIP-12", "TZIP-16", "TZIP-21"]
          , "authors": [
              "BUIDL Labs <https://buidllabs.io/>"
          ]
          , "homepage": "https://cryptocodeschool.in/tezos"
          , "source": {
              "tools": ["SmartPy"]
              , "location": "https://smartpy.io/templates/FA2.py"
          },
          "date": "2021-03-11",
          "tags": ["3D", "Cryptobot", "Collectables", "NFT"],
          "language": "en",
          "pictures": [
            {
                "link": "ipfs://QmXqZLz5UyEoYsn41CM9jf9cN2XurLQ8NML8hVTea2FnqT",
                "type": "logo"
            }
          ]
          , "views": list_of_views
          , "fa2-smartpy": {
                "configuration" :
                dict([(k, getattr(config, k)) for k in dir(config) if "__" not in k and k != 'my_map'])
            }
        }
        self.init_metadata("metadata_base", metadata_base)
        FA2.FA2_core.__init__(self, config, metadata,
            paused = False, administrator = admin,
            offer = sp.big_map(tkey = Offer.get_key_type(), tvalue = Offer.get_value_type()),
            initial_hodlers = sp.big_map(tkey = sp.TAddress, tvalue = sp.TNat))
            
    @sp.entry_point
    def offer_bot_for_sale(self, params):
        
        sp.verify( ~self.is_paused() , "CONTRACT IS PAUSED")
        
        sp.set_type(params.token_id, sp.TNat)
        sp.set_type(params.sale_price, sp.TMutez)
        
        # Make sure that the NFT token id is already present
        sp.verify(self.token_id_set.contains(self.data.all_tokens, params.token_id), "TOKEN ID NOT FOUND")
        
        # Make sure that sale_value is more than zero mutez
        sp.verify(params.sale_price > sp.mutez(0), "MIN VALUE SHOULD BE MORE THAN ZERO")
        user = self.ledger_key.make(sp.sender, params.token_id)
        
        #Make sure that the caller is the owner of NFT token id else throw error 
        sp.if self.data.ledger.contains(user):
            # Make sure user is the current owner of the NFT
            sp.if self.data.ledger[user].balance == 1:
                # Make NFT with token id open for offers
                self.data.offer[params.token_id] = sp.record(is_for_sale = True, seller = sp.sender, sale_value = params.sale_price)
            sp.else:
                sp.failwith(self.error_message.insufficient_balance())
        sp.else:
            sp.failwith("NOT OWNER OF NFT TOKEN ID")
    
    @sp.entry_point
    def bot_no_longer_for_sale(self, params):

        sp.verify( ~self.is_paused() , "CONTRACT IS PAUSED")
        
        sp.set_type(params.token_id, sp.TNat)
        
        # Make sure that the NFT token id is already present
        sp.verify(self.token_id_set.contains(self.data.all_tokens, params.token_id), "TOKEN ID NOT FOUND")
        
        # Make sure that token id is available for withdrwal from sale
        sp.verify(self.data.offer.contains(params.token_id), "NFT TOKEN ID NOT AVAILABLE FOR WITHDRWAL")
        
        user = self.ledger_key.make(sp.sender, params.token_id)
        
        #Make sure that the caller is the owner of NFT token id else throw error 
        sp.if self.data.ledger.contains(user):
            # Make sure user is the current owner of the NFT
            sp.if self.data.ledger[user].balance == 1:
                # Remove NFT token id from offers list
                del self.data.offer[params.token_id]
            sp.else:
                sp.failwith(self.error_message.insufficient_balance())
        sp.else:
            sp.failwith("NOT OWNER OF NFT TOKEN ID")
            
    @sp.entry_point
    def purchase_bot_at_sale_price(self, params):
        
        sp.verify( ~self.is_paused() , "CONTRACT IS PAUSED")
        
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
        # Make sure user is the current owner of the NFT
        sp.verify(self.data.ledger[user].balance == 1, self.error_message.insufficient_balance())
        
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
        
        sp.verify( ~self.is_paused() , "CONTRACT IS PAUSED")
        
        # Limit total supply to 10,000 3D Cryptobots
        sp.verify(sp.len(self.data.all_tokens) < 10000, "3D Cryptobot NFT creation limit exceeded")
        
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
        
    @sp.entry_point
    def transfer(self, params):
        
        sp.verify( ~self.is_paused() , "CONTRACT IS PAUSED")
        
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
                sp.verify(self.data.tokens.contains(tx.token_id),
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
                    # Make sure user is the current owner of the NFT
                    sp.if self.data.ledger[user].balance == 1:
                        # Remove NFT token id from offers list
                        sp.if self.data.offer.contains(tx.token_id):
                            del self.data.offer[tx.token_id]
        
    @sp.entry_point
    def burn(self, params):
        
        sp.verify(self.is_administrator(sp.sender), "INVALID_ADMIN_ADDRESS")
        
        sp.set_type(params.token_id, sp.TNat)
        sp.set_type(params.address, sp.TAddress)
        
        
        user = self.ledger_key.make(params.address, params.token_id)
        sp.if self.data.ledger.contains(user):
            sp.if self.data.ledger[user].balance != 1:
                sp.failwith("INVALID OWNER ADDRESS")
        sp.else:
            sp.failwith("INVALID OWNER ADDRESS")
            
        # Remove from offer for sale if there
        # Make sure that the caller is the owner of NFT token id else throw error 
        sp.if self.data.ledger.contains(user):
        # Remove NFT token id from offers list
            sp.if self.data.offer.contains(params.token_id):
                del self.data.offer[params.token_id]    
            
        # Remove token from ledger
        del self.data.ledger[user]
        
        # Remove token metadata
        del self.data.tokens[params.token_id]
        
        # Remove token from all_tokens list
        self.data.all_tokens.remove(params.token_id)
        

if "templates" not in __name__:
    @sp.add_test(name = "NFT Cryptobot collectables")
    def test():
        scenario = sp.test_scenario()
        scenario.h1("NFT Cryptobot collectables")

        scenario.table_of_contents()

        scenario.h2("Accounts")
        admin = sp.address("tz1bu5nmSkxYWRGU82HHHNcbTq1NciiyhntE")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")

        scenario.show([alice, bob])

        scenario.h2("Contract")
        
        c1 = Cryptobot( config = FA2.FA2_config(non_fungible = True, assume_consecutive_token_ids = False, store_total_supply = False),
                      metadata=sp.metadata_of_url("ipfs://QmRLicUooP6g88NYo8e59rhLJByywha1bASMEB9ysh5AYM"),
                      admin = admin
        )
        scenario += c1
        
        # Alice mints a nft
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 1,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice)
        # Alice puts nft on sale
        scenario += c1.offer_bot_for_sale(token_id = 1, sale_price = sp.mutez(1000)).run(sender = alice)
        # Alice withdraws nft from sale
        scenario += c1.bot_no_longer_for_sale(token_id = 1).run(sender = alice)
        
        # Bob mints a nft
        scenario += c1.mint(address = bob.address,
                            amount = 1,
                            token_id = 2,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = bob)
        # Bob puts nft on sale
        scenario += c1.offer_bot_for_sale(token_id = 2, sale_price = sp.mutez(1000)).run(sender = bob)
        
        # Alice transfer's nft to admin address directly
        scenario += c1.transfer(
                [
                    c1.batch_transfer.item(from_ = alice.address,
                                        txs = [
                                            sp.record(to_ = admin,
                                                      amount = 1,
                                                      token_id = 1)])
                ]).run(sender = alice)
        
        # Alice tries to put previously owned nft on sale
        scenario += c1.offer_bot_for_sale(token_id = 1, sale_price = sp.mutez(1000)).run(sender = alice, valid = False)
        
        # Alice tries to transfer back previously owned nft to own address
        scenario += c1.transfer(
                [
                    c1.batch_transfer.item(from_ = alice.address,
                                        txs = [
                                            sp.record(to_ = alice.address,
                                                      amount = 1,
                                                      token_id = 1)])
                ]).run(sender = alice, valid = False)
        
        # Admin puts nft on sale
        scenario += c1.offer_bot_for_sale(token_id = 1, sale_price = sp.mutez(1000)).run(sender = admin)
        
        # Admin burns the owned nft
        scenario += c1.burn(token_id = 1, address = admin).run(sender = admin)
        
        # Alice again mints nft with token_id 1
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 1,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice)
        
        # Alice purchases bob nft
        scenario += c1.purchase_bot_at_sale_price(token_id = 2).run(sender = alice, amount = sp.mutez(1000))
        
        # Bob tries to put previously own nft on sale
        scenario += c1.offer_bot_for_sale(token_id = 2, sale_price = sp.mutez(1000)).run(sender = bob, valid = False)
        
        # Admin tries to burn token with wrong owner
        scenario += c1.burn(token_id = 2, address = bob.address).run(sender = admin, valid = False)
        
        # -------------------
        
        # Alice mints another nft
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 3,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice)
        
        # Alice puts nft on sale with price of 0 xtz
        scenario += c1.offer_bot_for_sale(token_id = 3, sale_price = sp.mutez(0)).run(sender = alice, valid = False)
        
        # Alice tries to burn previously created nft 
        scenario += c1.burn(token_id = 3, address = alice.address).run(sender = alice, valid = False)
        
        # Alice puts bot on sale with price more than 0 xtz
        scenario += c1.offer_bot_for_sale(token_id = 3, sale_price = sp.mutez(2000)).run(sender = alice)
        
        # Alice puts bot on sale twice
        scenario += c1.offer_bot_for_sale(token_id = 3, sale_price = sp.mutez(3000)).run(sender = alice)
        
        
        # -------------------
        
        # Alice mints another nft
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 4,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice)
        # Alice transfers nft to bob
        scenario += c1.transfer(
                [
                    c1.batch_transfer.item(from_ = alice.address,
                                        txs = [
                                            sp.record(to_ = bob.address,
                                                      amount = 1,
                                                      token_id = 4)])
                ]).run(sender = alice)
        # Make sure that only owner of nft can put it on sale
        scenario += c1.offer_bot_for_sale(token_id = 4, sale_price = sp.mutez(2000)).run(sender = alice, valid = False)
        
        scenario += c1.offer_bot_for_sale(token_id = 4, sale_price = sp.mutez(2000)).run(sender = bob)
        # Make sure bot can be withdrawn by the owner only
        scenario += c1.bot_no_longer_for_sale(token_id = 4).run(sender = alice, valid = False)
        
        # Make sure bot can be purchased at sale value only
        scenario += c1.purchase_bot_at_sale_price(token_id = 4).run(sender = alice, amount = sp.mutez(1000), valid = False)
        
        scenario += c1.purchase_bot_at_sale_price(token_id = 4).run(sender = alice, amount = sp.mutez(2000))

        # -------------------
        
        # Allow one xtz address to mint only 5 nft bots
        
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 5,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice)
        
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 6,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice, valid = False)
        
        # -------------------
        
        # Admin pauses the contract 
        scenario += c1.set_pause(True).run(sender = admin)
        
        # Make sure all entry_point are inaccessible after contract is paused 
        scenario += c1.mint(address = alice.address,
                            amount = 1,
                            token_id = 4,
                            metadata = {'': sp.bytes_of_string('')}).run(sender = alice, valid = False)
        
        scenario += c1.offer_bot_for_sale(token_id = 4, sale_price = sp.mutez(3000)).run(sender = alice, valid = False)
        
        scenario += c1.bot_no_longer_for_sale(token_id = 4).run(sender = alice, valid = False)
        
        scenario += c1.purchase_bot_at_sale_price(token_id = 4).run(sender = alice, amount = sp.mutez(3000), valid = False)
        
        scenario += c1.transfer(
                [
                    c1.batch_transfer.item(from_ = alice.address,
                                        txs = [
                                            sp.record(to_ = alice.address,
                                                      amount = 1,
                                                      token_id = 4)])
                ]).run(sender = alice, valid = False)
        
        # -------------------