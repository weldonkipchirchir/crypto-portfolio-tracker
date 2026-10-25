"""Heuristic review suggestions from persisted chain events, never accounting entries."""
from collections import defaultdict
from decimal import Decimal,InvalidOperation,localcontext

WARNINGS=['Transfer patterns are review suggestions; swaps are not verified.',
          'Internal transfers and missing history may change this interpretation.',
          'Token identity and purchase cost require review; no price or P&L is inferred.']

def _number(value):
    if len(str(value))>350:return None
    try:result=Decimal(str(value))
    except (InvalidOperation,ValueError):return None
    if not result.is_finite() or result<0 or len(str(value))>400:return None
    if result.adjusted()>78 or not -255<=result.as_tuple().exponent<=78:return None
    return result

def _text(value):return format(value,'f')

def build_reviews(history_records,review_statuses=None):
    """Return deterministic review groups; sent/received are always asset lists.

    review_statuses optionally maps suggestion ID to a status string. This does not
    mutate history, infer prices or create trades. Native fees are metadata and
    are not included in sent quantities. Only confirmed directional events count.
    """
    groups=defaultdict(list);seen=set()
    for row in history_records:
        if row.get('status')!='confirmed':continue
        key=(row.get('wallet_id'),row.get('chain'),row.get('hash'))
        if None in key or not row.get('event_id'):continue
        dedup=key[:2]+(row['event_id'],)
        if dedup in seen:continue
        seen.add(dedup);groups[key].append(row)
    suggestions=[]
    with localcontext() as ctx:
        ctx.prec=500
        for (wallet_id,chain,txhash),events in groups.items():
            if any(event.get('review_eligible') is False for event in events):continue
            nets=defaultdict(Decimal);names={};fees=[]
            for event in events:
                # Gas metadata can belong to a zero-value contract interaction.
                if event.get('kind') in ('native_transfer','contract_activity') or event.get('asset_id')==str(chain)+':native':
                    fee=_number(event.get('fee'))
                    if fee is not None:fees.append(fee)
                direction=event.get('direction')
                if direction not in ('in','out'):continue
                quantity=_number(event.get('quantity'))
                asset_id=event.get('asset_id')
                if quantity is None or quantity==0 or not asset_id:continue
                names[asset_id]=min(str(event.get('asset') or asset_id),names.get(asset_id,str(event.get('asset') or asset_id)))
                nets[asset_id]+=quantity if direction=='in' else -quantity
            sent=[];received=[]
            for asset_id,quantity in sorted(nets.items()):
                if quantity==0:continue
                item={'asset_id':asset_id,'asset':names[asset_id],'quantity':_text(abs(quantity))}
                (received if quantity>0 else sent).append(item)
            count=len(sent)+len(received)
            if not count:continue
            if count>2:kind='complex_activity'
            elif len(sent)==1 and len(received)==1:kind='swap_candidate'
            elif not sent and len(received)==1:kind='acquisition_review'
            elif not received and len(sent)==1:kind='disposal_review'
            else:kind='complex_activity'
            identifier=str(wallet_id)+':'+str(chain)+':'+str(txhash)
            dates=sorted(str(e['date']) for e in events if e.get('date'))
            if not dates:continue
            labels=sorted(str(e.get('wallet_label') or '') for e in events)
            status=(review_statuses or {}).get(identifier,'pending')
            if not isinstance(status,str):status='pending'
            suggestions.append({'id':identifier,'kind':kind,'type':kind,'wallet_id':wallet_id,'chain':chain,
                'hash':txhash,'date':dates[0] if dates else None,'wallet_label':labels[0] if labels else '',
                'sent':sent,'received':received,'native_fee':_text(max(fees)) if fees else None,
                'status':status,'warnings':list(WARNINGS)})
    return sorted(suggestions,key=lambda item:(item['date'] or '',item['id']),reverse=True)



