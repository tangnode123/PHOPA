% =====================================================================
% P-HOPA3D : NAIVE baseline encoding (naive.lp)
% Straightforward 3D generalization of the HOPA ASP rules:
%   (N1) yaw AND pitch guessed for EVERY object;
%   (N2) elevation checks over the full 3-way (DX,DY,DZ) join;
%   (N3) distance checks over the full 3-way (DX,DY,DZ) join.
% Companion to input facts: *_inst.lp (instance) + *_geom.lp (geometry
% library tables az_angle/3, q/3 -- IDENTICAL input for naive.lp).
%
% (Kept identical: input handling, disjunctive/presumed layer,
%  locations, horizontal azimuth via haz, azimuth/range/same3d checks,
%  extended objects, inference.)
% REMOVED structural choices of proj.lp:
%   (P1) orientation variables are created ONLY for objects that occur
%        in orientation-sensitive constraints (need_yaw/need_pitch);
%   (P2) vertical (elevation) sector checks run over the two-step join
%        hd(P,R,Q) [2D] x zdist(P,R,DZ) [1D]  -- never over the full
%        3-way (DX,DY,DZ) product;
%   (P3) distance checks run over nd2(P,R,U) [2D, dedup] x zdist [1D].
% =====================================================================

% ---------- optional input predicates ----------
#defined invalid_loc/3.
#defined mandatory/1.
#defined presumed/1.
#defined presumed_one_sided3d/5.
#defined presumed_direction/3.
#defined explain_mode/0.
#defined toinfer_orient/1.
#defined toinfer_pos/1.
#defined toinfer_distrel/2.
#defined toinfer_os3d/4.
#defined min_gap/4.
#defined azim/4.
#defined azim_range/5.
#defined distance/4.
#defined distance_sq/4.
#defined distance_range/5.
#defined pitch/3.
#defined pitch_range/4.
#defined direction/3.
#defined direction_range/4.
#defined location/5.
#defined same3d/5.
#defined one_sided3d/5.
#defined dist_rel/4.
#defined extent/4.
#defined existdisj/1.
#defined disjrelation/9.
#defined disj_index/2.
#defined hd/3.
#defined nd2/3.
#defined dsq/3.

% ---------- defeasible layer ----------
act(N) :- constraint_id(N), not drop(N).
{drop(N)} <= 1 :- explain_mode, not mandatory(N), constraint_id(N).
:~ drop(N). [1@1,N]

{violated(N)} <= 1 :- presumed(N).
:~ violated(N). [1@2,N]
one_sided3d(N,K,L,I,J) :- presumed_one_sided3d(N,K,L,I,J), not violated(N).
direction(N,K,A)       :- presumed_direction(N,K,A), not violated(N).

% ---------- disjunctive constraints: choose exactly one disjunct ----------
{chosen(N,D) : disj_index(N,D)} = 1 :- existdisj(N).
one_sided3d(N,P1,P2,P3,P4)   :- act(N), chosen(N,D), disjrelation(N,D,1,P1,P2,P3,P4,_,_).
dist_rel(N,P1,P2,P3)         :- act(N), chosen(N,D), disjrelation(N,D,2,P1,P2,P3,_,_,_).
distance(N,P1,P2,P3)         :- act(N), chosen(N,D), disjrelation(N,D,3,P1,P2,P3,_,_,_).
distance_range(N,P1,P2,P3,P4):- act(N), chosen(N,D), disjrelation(N,D,4,P1,P2,P3,P4,_,_).
direction(N,P1,P2)           :- act(N), chosen(N,D), disjrelation(N,D,5,P1,P2,_,_,_,_).
direction_range(N,P1,P2,P3)  :- act(N), chosen(N,D), disjrelation(N,D,6,P1,P2,P3,_,_,_).
pitch(N,P1,P2)               :- act(N), chosen(N,D), disjrelation(N,D,7,P1,P2,_,_,_,_).
pitch_range(N,P1,P2,P3)      :- act(N), chosen(N,D), disjrelation(N,D,8,P1,P2,P3,_,_,_).
azim(N,P1,P2,P3)             :- act(N), chosen(N,D), disjrelation(N,D,9,P1,P2,P3,_,_,_).
azim_range(N,P1,P2,P3,P4)    :- act(N), chosen(N,D), disjrelation(N,D,10,P1,P2,P3,P4,_,_).
location(N,P1,P2,P3,P4)      :- act(N), chosen(N,D), disjrelation(N,D,11,P1,P2,P3,P4,_,_).
distance_sq(N,P1,P2,P3)      :- act(N), chosen(N,D), disjrelation(N,D,12,P1,P2,P3,_,_,_).
same3d(N,P1,P2,P3,P4)        :- act(N), chosen(N,D), disjrelation(N,D,13,P1,P2,P3,P4,_,_).

% ---------- grid ----------
grid_x(X) :- sx(S), X = 1..S.
grid_y(Y) :- sy(S), Y = 1..S.
grid_z(Z) :- sz(S), Z = 1..S.
has_point(P) :- point(_,P).

% ---------- locations ----------
loc_known(P) :- point(K,P), location(N,K,_,_,_), act(N).
xloc(P,X) :- point(K,P), location(N,K,X,_,_), act(N).
yloc(P,Y) :- point(K,P), location(N,K,_,Y,_), act(N).
zloc(P,Z) :- point(K,P), location(N,K,_,_,Z), act(N).
{xloc(P,X) : grid_x(X)} = 1 :- has_point(P), not loc_known(P).
{yloc(P,Y) : grid_y(Y)} = 1 :- has_point(P), not loc_known(P).
{zloc(P,Z) : grid_z(Z)} = 1 :- has_point(P), not loc_known(P).
:- invalid_loc(X,Y,Z), xloc(P,X), yloc(P,Y), zloc(P,Z).
:- xloc(P,X1), xloc(P,X2), X1 != X2.
:- yloc(P,Y1), yloc(P,Y2), Y1 != Y2.
:- zloc(P,Z1), zloc(P,Z2), Z1 != Z2.

% same3d forces coincident locations
:- same3d(N,K,L,_,_), act(N), point(K,P), point(L,R), xloc(P,X1), xloc(R,X2), X1 != X2.
:- same3d(N,K,L,_,_), act(N), point(K,P), point(L,R), yloc(P,Y1), yloc(R,Y2), Y1 != Y2.
:- same3d(N,K,L,_,_), act(N), point(K,P), point(L,R), zloc(P,Z1), zloc(R,Z2), Z1 != Z2.

% ---------- orientation variables: CONDITIONAL creation (P1) ----------
need_yaw(L) :- one_sided3d(N,_,L,_,_), act(N).
need_yaw(K) :- direction(N,K,_), act(N).
need_yaw(K) :- direction_range(N,K,_,_), act(N).
need_yaw(K) :- same3d(N,K,_,_,_), act(N).
need_yaw(L) :- same3d(N,_,L,_,_), act(N).
need_yaw(K) :- toinfer_orient(K).
orient_specified(K) :- direction(N,K,_), act(N).
ye(E) :- ra(R), U = 360/R - 1, E = 0..U.
{yawb(K,E) : ye(E)} = 1 :- object(K), not orient_specified(K).
yaw(K,A) :- yawb(K,E), ra(R), A = E*R.
yaw(K,A) :- direction(N,K,A), act(N).

need_pitch(K) :- pitch(N,K,_), act(N).
need_pitch(K) :- pitch_range(N,K,_,_), act(N).
need_pitch(K) :- same3d(N,K,_,_,_), act(N).
need_pitch(L) :- same3d(N,_,L,_,_), act(N).
pitch_specified(K) :- pitch(N,K,_), act(N).
pe(F) :- re(R), U = 180/R, F = 0..U.
{pitchb(K,F) : pe(F)} = 1 :- object(K), not pitch_specified(K).
pitch(K,B) :- pitchb(K,F), re(R), B = F*R - 90.
pitch(K,B) :- pitch(N,K,B), act(N).

% functional uniqueness of orientation values (conflicting direction/pitch facts
% or disjunct materializations must make the instance UNSAT, not duplicate atoms)
:- yaw(K,A1), yaw(K,A2), A1 != A2.
:- pitch(K,B1), pitch(K,B2), B1 != B2.

% ---------- vectors over needed ordered point pairs ----------
need_vec(P,R) :- one_sided3d(N,K,L,_,_), act(N), point(K,P), point(L,R).
need_vec(P,R) :- dist_rel(N,K,L,_), act(N), point(K,P), point(L,R).
need_vec(P,R) :- distance(N,K,L,_), act(N), point(K,P), point(L,R).
need_vec(P,R) :- distance_sq(N,K,L,_), act(N), point(K,P), point(L,R).
need_vec(P,R) :- distance_range(N,K,L,_,_), act(N), point(K,P), point(L,R).
need_vec(R,P) :- azim(N,K,L,_), act(N), point(K,P), point(L,R).
need_vec(R,P) :- azim_range(N,K,L,_,_), act(N), point(K,P), point(L,R).
need_vec(P,R) :- toinfer_os3d(K,L,_,_), point(K,P), point(L,R).
need_vec(P,R) :- toinfer_distrel(K,L), point(K,P), point(L,R).

xdist(A,B,D) :- need_vec(A,B), xloc(A,X1), xloc(B,X2), D = X1-X2.
ydist(A,B,D) :- need_vec(A,B), yloc(A,Y1), yloc(B,Y2), D = Y1-Y2.
zdist(A,B,D) :- need_vec(A,B), zloc(A,Z1), zloc(B,Z2), D = Z1-Z2.

% ---------- horizontal component (2D table join) ----------
haz(A,B,ANG) :- need_vec(A,B), xdist(A,B,DX), ydist(A,B,DY), az_angle(DX,DY,ANG).
haz_any(A,B) :- haz(A,B,_).
% coincident points: relation undefined -> forbid
:- one_sided3d(N,K,L,_,_), act(N), point(K,P), point(L,R), not haz_any(P,R).
:- azim(N,K,L,_), act(N), point(K,P), point(L,R), not haz_any(R,P).
:- azim_range(N,K,L,_,_), act(N), point(K,P), point(L,R), not haz_any(R,P).

% ---------- one_sided3d horizontal sector checks ----------
% vector L->K = (xdist(P,R), ydist(P,R)) with P=point(K), R=point(L)
% psi = (AZ - yaw_L + 360) \ 360 ; sector width W = 90/MH
% I odd, non-wrapping open interval (LO,HI)
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), IP = I\2, IP == 1,
   mh(G), W = 90/G, LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO < HI,
   haz(P,R,A), yaw(L,T), PS = (A - T + 360)\360, PS <= LO.
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), IP = I\2, IP == 1,
   mh(G), W = 90/G, LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO < HI,
   haz(P,R,A), yaw(L,T), PS = (A - T + 360)\360, PS >= HI.
% I odd, wrapping interval
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), IP = I\2, IP == 1,
   mh(G), W = 90/G, LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO > HI,
   haz(P,R,A), yaw(L,T), PS = (A - T + 360)\360, PS <= LO, PS >= HI.
% I even (linear): exact equality
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), IP = I\2, IP == 0,
   mh(G), W = 90/G, LO = (I*W)\360,
   haz(P,R,A), yaw(L,T), PS = (A - T + 360)\360, PS != LO.

% ---------- [NAIVE] vertical sector checks: full 3-way (DX,DY,DZ) join ----------
% J odd interior
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), JP = J\2, JP == 1,
   JM = J-1, tb(JM,T1), xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,Q),
   Q > 0, DZ*1000 <= T1*Q.
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), JP = J\2, JP == 1,
   JPL = J+1, tb(JPL,T2), xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,Q),
   Q > 0, DZ*1000 >= T2*Q.
% J even interior (linear elevation)
:- one_sided3d(N,K,L,I,J), act(N), point(K,P), point(L,R), JP = J\2, JP == 0,
   J > 0, mv(G), TOP = 2*G, J < TOP, tb(J,T),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,Q), DZ*1000 != T*Q.
% J = 0 : straight down
:- one_sided3d(N,K,L,I,0), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,Q), Q > 0.
:- one_sided3d(N,K,L,I,0), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,0), DZ >= 0.
% J = 2*MV : straight up
:- one_sided3d(N,K,L,I,J), act(N), mv(G), J == 2*G, point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,Q), Q > 0.
:- one_sided3d(N,K,L,I,J), act(N), mv(G), J == 2*G, point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), q(DX,DY,0), DZ <= 0.

% ---------- [NAIVE] distance constraints: full 3-way (DX,DY,DZ) join ----------
:- dist_rel(N,K,L,Uc), act(N), point(K,P), point(L,R), drel(Uc,LB,UB),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ < LB*LB.
:- dist_rel(N,K,L,Uc), act(N), point(K,P), point(L,R), drel(Uc,LB,UB),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ > UB*UB.
:- distance(N,K,L,D), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ != D*D.
:- distance_sq(N,K,L,DS), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ != DS.
:- distance_range(N,K,L,D1,D2), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ < D1*D1.
:- distance_range(N,K,L,D1,D2), act(N), point(K,P), point(L,R),
   xdist(P,R,DX), ydist(P,R,DY), zdist(P,R,DZ), DX*DX + DY*DY + DZ*DZ > D2*D2.

% ---------- absolute azimuth constraints (vector K->L = order (R,P)) ----------
:- azim(N,K,L,A), act(N), point(K,P), point(L,R), haz(R,P,ANG), ANG != A.
:- azim_range(N,K,L,A1,A2), act(N), point(K,P), point(L,R), haz(R,P,ANG), A1 <= A2, ANG < A1.
:- azim_range(N,K,L,A1,A2), act(N), point(K,P), point(L,R), haz(R,P,ANG), A1 <= A2, ANG > A2.
:- azim_range(N,K,L,A1,A2), act(N), point(K,P), point(L,R), haz(R,P,ANG), A1 > A2, ANG < A1, ANG > A2.

% ---------- yaw / pitch range checks ----------
:- direction_range(N,K,A1,A2), act(N), yaw(K,T), A1 <= A2, T < A1.
:- direction_range(N,K,A1,A2), act(N), yaw(K,T), A1 <= A2, T > A2.
:- direction_range(N,K,A1,A2), act(N), yaw(K,T), A1 > A2, T < A1, T > A2.
:- pitch_range(N,K,B1,B2), act(N), pitch(K,B), B < B1.
:- pitch_range(N,K,B1,B2), act(N), pitch(K,B), B > B2.

% ---------- same3d orientation sectors ----------
% yaw delta sector I with granularity MH
:- same3d(N,K,L,I,J), act(N), IP = I\2, IP == 1, mh(G), W = 90/G,
   LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO < HI,
   yaw(K,TK), yaw(L,TL), DY = (TK - TL + 360)\360, DY <= LO.
:- same3d(N,K,L,I,J), act(N), IP = I\2, IP == 1, mh(G), W = 90/G,
   LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO < HI,
   yaw(K,TK), yaw(L,TL), DY = (TK - TL + 360)\360, DY >= HI.
:- same3d(N,K,L,I,J), act(N), IP = I\2, IP == 1, mh(G), W = 90/G,
   LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO > HI,
   yaw(K,TK), yaw(L,TL), DY = (TK - TL + 360)\360, DY <= LO, DY >= HI.
:- same3d(N,K,L,I,J), act(N), IP = I\2, IP == 0, mh(G), W = 90/G, LO = (I*W)\360,
   yaw(K,TK), yaw(L,TL), DY = (TK - TL + 360)\360, DY != LO.
% pitch delta sector J with granularity MV (4*MV sectors over the circle)
:- same3d(N,K,L,I,J), act(N), JQ = J\2, JQ == 1, mv(G), W = 90/G,
   LO = ((J-1)*W)\360, HI = ((J+1)*W)\360, LO < HI,
   pitch(K,BK), pitch(L,BL), DP = (BK - BL + 360)\360, DP <= LO.
:- same3d(N,K,L,I,J), act(N), JQ = J\2, JQ == 1, mv(G), W = 90/G,
   LO = ((J-1)*W)\360, HI = ((J+1)*W)\360, LO < HI,
   pitch(K,BK), pitch(L,BL), DP = (BK - BL + 360)\360, DP >= HI.
:- same3d(N,K,L,I,J), act(N), JQ = J\2, JQ == 1, mv(G), W = 90/G,
   LO = ((J-1)*W)\360, HI = ((J+1)*W)\360, LO > HI,
   pitch(K,BK), pitch(L,BL), DP = (BK - BL + 360)\360, DP <= LO, DP >= HI.
:- same3d(N,K,L,I,J), act(N), JQ = J\2, JQ == 0, mv(G), W = 90/G, LO = (J*W)\360,
   pitch(K,BK), pitch(L,BL), DP = (BK - BL + 360)\360, DP != LO.

% ---------- extended objects: AABB non-overlap + min_gap ----------
ext(A,EX,EY,EZ) :- extent(A,EX,EY,EZ).
ext(A,0,0,0) :- object(A), not extent(A,_,_,_).
oxloc(A,X) :- point(A,P), xloc(P,X).
oyloc(A,Y) :- point(A,P), yloc(P,Y).
ozloc(A,Z) :- point(A,P), zloc(P,Z).
objpair_ext(A,B) :- ext(A,_,_,_), ext(B,_,_,_), A < B, ext(A,EXA,EYA,EZA), ext(B,EXB,EYB,EZB),
                    EXA + EYA + EZA + EXB + EYB + EZB > 0.
xov(A,B) :- objpair_ext(A,B), oxloc(A,X1), oxloc(B,X2), ext(A,EXA,_,_), ext(B,EXB,_,_),
            X1 - X2 <= EXA + EXB, X2 - X1 <= EXA + EXB.
yov(A,B) :- objpair_ext(A,B), oyloc(A,Y1), oyloc(B,Y2), ext(A,_,EYA,_), ext(B,_,EYB,_),
            Y1 - Y2 <= EYA + EYB, Y2 - Y1 <= EYA + EYB.
zov(A,B) :- objpair_ext(A,B), ozloc(A,Z1), ozloc(B,Z2), ext(A,_,_,EZA), ext(B,_,_,EZB),
            Z1 - Z2 <= EZA + EZB, Z2 - Z1 <= EZA + EZB.
:- xov(A,B), yov(A,B), zov(A,B).

xclose(K,L) :- min_gap(N,K,L,G), act(N), oxloc(K,X1), oxloc(L,X2), ext(K,EXK,_,_), ext(L,EXL,_,_),
               X1 - X2 < EXK + EXL + G, X2 - X1 < EXK + EXL + G.
yclose(K,L) :- min_gap(N,K,L,G), act(N), oyloc(K,Y1), oyloc(L,Y2), ext(K,_,EYK,_), ext(L,_,EYL,_),
               Y1 - Y2 < EYK + EYL + G, Y2 - Y1 < EYK + EYL + G.
zclose(K,L) :- min_gap(N,K,L,G), act(N), ozloc(K,Z1), ozloc(L,Z2), ext(K,_,_,EZK), ext(L,_,_,EZL),
               Z1 - Z2 < EZK + EZL + G, Z2 - Z1 < EZK + EZL + G.
:- min_gap(N,K,L,G), act(N), xclose(K,L), yclose(K,L), zclose(K,L).

% ---------- inference of new knowledge (scenarios only) ----------
inferred_orient(K,A) :- toinfer_orient(K), yaw(K,A).
inferred_pos(K,X,Y,Z) :- toinfer_pos(K), oxloc(K,X), oyloc(K,Y), ozloc(K,Z).
inferred_distrel(K,L,Uc) :- toinfer_distrel(K,L), point(K,P), point(L,R), dsq(P,R,D3),
                            drel(Uc,LB,UB), D3 >= LB*LB, D3 <= UB*UB.
inf_needed :- toinfer_os3d(_,_,_,_).
psdom(PS) :- inf_needed, ra(R), U = 360 - R, E = 0..(U/R), PS = E*R.
isecdom(I,W) :- inf_needed, mh(GH), W = 90/GH, IMAX = 4*GH - 1, I = 0..IMAX.
hsec_holds(PS,I,W) :- inf_needed, psdom(PS), isecdom(I,W), IP = I\2, IP == 1,
                      LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO < HI, PS > LO, PS < HI.
hsec_holds(PS,I,W) :- inf_needed, psdom(PS), isecdom(I,W), IP = I\2, IP == 1,
                      LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO > HI, PS > LO.
hsec_holds(PS,I,W) :- inf_needed, psdom(PS), isecdom(I,W), IP = I\2, IP == 1,
                      LO = ((I-1)*W)\360, HI = ((I+1)*W)\360, LO > HI, PS < HI.
hsec_holds(PS,I,W) :- inf_needed, psdom(PS), isecdom(I,W), IP = I\2, IP == 0,
                      LO = (I*W)\360, PS == LO.
zdom(DZ) :- inf_needed, sz(S), LO2 = 1 - S, HI2 = S - 1, DZ = LO2..HI2.
qdom(Q) :- inf_needed, q(_,_,Q).
jdomv(J,GV) :- inf_needed, mv(GV), JT = 2*GV, J = 0..JT.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), JQ = J\2, JQ == 1,
                         J > 0, TOP = 2*GV, J < TOP, JM = J-1, JPL = J+1,
                         tb(JM,T1), tb(JPL,T2), Q > 0, DZ*1000 > T1*Q, DZ*1000 < T2*Q.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), JQ = J\2, JQ == 0,
                         J > 0, TOP = 2*GV, J < TOP, tb(J,T), DZ*1000 == T*Q.
% boundary odd sectors: tb(0)/tb(2*GV) sentinels are intentionally absent --
% on the CONSTRAINT side absence means infinite bound (correct), but on the
% INFERENCE side the generic rule would never fire. Special-case them:
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), JQ = J\2, JQ == 1,
                         J == 1, TOP = 2*GV, J < TOP-1, JPL = J+1, tb(JPL,T2), Q > 0, DZ*1000 < T2*Q.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), JQ = J\2, JQ == 1,
                         TOP = 2*GV, J == TOP-1, J > 1, JM = J-1, tb(JM,T1), Q > 0, DZ*1000 > T1*Q.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), JQ = J\2, JQ == 1,
                         J == 1, TOP = 2*GV, J == TOP-1, Q > 0.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), J == 0, Q == 0, DZ < 0.
vsec_holds(DZ,Q,J,GV) :- inf_needed, zdom(DZ), qdom(Q), jdomv(J,GV), TOP = 2*GV, J == TOP, Q == 0, DZ > 0.
inferred_os3d(K,L,I,J) :- toinfer_os3d(K,L,GH,GV), point(K,P), point(L,R),
                          haz(P,R,A), yaw(L,T), mh(GH), WH = 90/GH, PS = (A - T + 360)\360,
                          hsec_holds(PS,I,WH), hd(P,R,Q), zdist(P,R,DZ),
                          vsec_holds(DZ,Q,J,GV).
