importhashlib


defdouble_sha256(data:bytes)->bytes:
"""BerechnetSHA-256(SHA-256(data))."""
returnhashlib.sha256(hashlib.sha256(data).digest()).digest()


defcalculate_merkle_root(tx_hashes:list[bytes])->bytes:
"""BerechnetdenMerkleRootauseinerListevonTransaktions-Hashes
(inLittle-Endian/InternalByteOrder).
"""
ifnottx_hashes:
returnb"\x00"*32
current_level=list(tx_hashes)
whilelen(current_level)>1:
iflen(current_level)%2!=0:
current_level.append(current_level[-1])

next_level=[]
foriinrange(0,len(current_level),2):
combined=current_level[i]+current_level[i+1]
next_level.append(double_sha256(combined))
current_level=next_level

returncurrent_level[0]


defbuild_merkle_branch(tx_hashes:list[bytes])->list[bytes]:
"""ErstelltdenMerkleBranchfürdieCoinbase-Transaktion(Index0).

GibtdieListederPartner-Hasheszurück,diederStratum-Minerbenötigt,
umdenMerkleRootzuberechnen.
"""
ifnottx_hashes:
return[]

branch:list[bytes]=[]
current_level=list(tx_hashes)

whilelen(current_level)>1:
iflen(current_level)%2!=0:
current_level.append(current_level[-1])
#DerPartnerfürIndex0liegtaufdiesemLevelimmeranIndex1
branch.append(current_level[1])

next_level=[]
foriinrange(0,len(current_level),2):
combined=current_level[i]+current_level[i+1]
next_level.append(double_sha256(combined))

current_level=next_level

returnbranch
